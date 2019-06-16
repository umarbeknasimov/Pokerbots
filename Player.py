
from pokerbots import Bot, parse_args, run_bot
from pokerbots.actions import FoldAction, CallAction, CheckAction, BetAction, RaiseAction, ExchangeAction
from scipy import stats
import numpy as np


try:
    from pbots_calc import calc
except ImportError:
    calc = None
    print "Warning: could not import calc"

import random

"""
Simple example pokerbot, written in python.
"""

class Player(Bot):

    def __init__(self):
        Bot.__init__(self)
        self.stop = False
        self.games = {"win":0, "loss":0, "tie":0}
        self.fold_before_flop = 0
        self.fold_before_turn = 0 
        self.bluff_before_flop = 0
        self.bluff_before_turn = 0
        self.exchange_count=0
        self.opp_bluff_before_flop = False
        self.opp_bluff_before_turn = False

        # dictionary that maps opponent's first bet after river (int) to the strength of their hand (float)
        # self.opp_bet_strength = {}

        # two lists that contain opponent's first bet after river and strength of their hand, with corresponding indices
        self.opp_river_bet = []
        self.opp_river_strength = []
        self.slope = 0 # default slope value, will change later
        self.intercept = 0.8 # default intercept value, will change later

        self.opp_check = 0 # check the number of checks our opponent makes

        self.fold = 0 # checks the number of times we fold

        self.check_player = True
        self.opp = 'B' # will check and change to A later if appropriate
        self.num_of_bets = 0 #check the number of times the opponent bets


    def handle_new_game(self, new_game):
        '''
        Called when a new game starts. Called exactly once.

        Arguments:
        new_game: the pokerbots.Game object.

        Returns:
        Nothing.
        '''
        self.predicted_strength = 0

    def handle_new_round(self, game, new_round):
        '''
        Called when a new round starts. Called Game.num_rounds times.

        Arguments:
        game: the pokerbots.Game object for the new round.
        new_round: the new pokerbots.Round object.

        Returns:
        Nothing.
        '''
        # print("round " + str(new_round.hand_num))
        self.exchange_count=0
        self.discarded_cards = set()
        self.opp_check = 0
        self.checked_exchanges = False

        print("round " + str(new_round.hand_num))

    def handle_round_over(self, game, round, pot, cards, opponent_cards, board_cards, result, new_bankroll, new_opponent_bankroll, move_history):
        '''
        Called when a round ends. Called Game.num_rounds times.

        Arguments:
        game: the pokerbots.Game object.
        round: the pokerbots.Round object.
        pot: the pokerbots.Pot object.
        cards: the cards you held when the round ended.
        opponent_cards: the cards your opponent held when the round ended, or None if they never showed.
        board_cards: the cards on the board when the round ended.
        result: 'win', 'loss' or 'tie'
        new_bankroll: your total bankroll at the end of this round.
        new_opponent_bankroll: your opponent's total bankroll at the end of this round.
        move_history: a list of moves that occurred during this round, earliest moves first.

        Returns:
        Nothing.
        '''

        self.num_of_bets = 0
        
        if new_bankroll > (1000-round.hand_num)*1.5+10:
            self.stop = True

        self.games[result]+=1
        if round.hand_num<=50:  
            flop = False
            turn = False
            for moves in move_history:
                if "FLOP" in moves:
                    flop = True 
                if "TURN" in moves: 
                    turn = True

                if self.opp == 'B':
                    if moves == "FOLD:A":
                        if not flop:
                            self.fold_before_flop +=1
                        elif not turn:
                            self.fold_before_turn +=1
                    if moves == "FOLD:" + self.opp:
                        if not flop:
                            self.bluff_before_flop +=1
                        elif not turn:
                            self.bluff_before_turn +=1
                else: # self.opp == 'A'
                    if moves == "FOLD:B":
                        if not flop:
                            self.fold_before_flop +=1
                        elif not turn:
                            self.fold_before_turn +=1
                    if moves == "FOLD:A":
                        if not flop:
                            self.bluff_before_flop +=1
                        elif not turn:
                            self.bluff_before_turn +=1
        # print(self.fold_before_flop, self.fold_before_turn, self.bluff_before_turn, self.bluff_before_flop)


        # save info on how much B bet and the strength of their hand

        if len(board_cards) == 5 and opponent_cards != None: # make sure after river and opponent revealed cards
        	# iterate through move history to look for opponent's first bet after river
            river = False
            for element in move_history:
                if "RIVER" in element:
                    river = True

                if river and "BET" in element: # only look at moves that are bets after river
        			# move is in the form "BET:bet_amt:player" so cut first four chars of move and splice the rest by the colon
                    info = element[4:].split(':') 
                    if info[1] == self.opp: # only care about B's bet
        				# add key info[0] with value strength of opponent_cards
                        if calc is not None:
                            opp_result = calc(''.join(opponent_cards) + ':xx', ''.join(board_cards), '', 1000)
                            self.opp_river_bet.append(int(info[0]))
                            self.opp_river_strength.append(opp_result.ev[0])
                        else:
                            opp_result = random.random()
        				# self.opp_bet_strength[int(info[0])] = opp_result.ev[0]
                        
       
    def get_action(self, game, round, pot, cards, board_cards, legal_moves, cost_func, move_history, time_left, min_amount=None, max_amount=None):
        '''
        Where the magic happens - your code should implement this function.
        Called any time the server needs an action from your bot.

        Arguments:
        game: the pokerbots.Game object.
        round: the pokerbots.Round object.
        pot: the pokerbots.Pot object.
        cards: an array of your cards, in common format.
        board_cards: an array of cards on the board. This list has length 0, 3, 4, or 5.
        legal_moves: a set of the move classes that are legal to make.
        cost_func: a function that takes a move, and returns additional cost of that move. Your returned move will raise your pot.contribution by this amount.
        move_history: a list of moves that have occurred during this round so far, earliest moves first.
        time_left: a float of the number of seconds your bot has remaining in this match (not round).
        min_amount: if BetAction or RaiseAction is valid, the smallest amount you can bet or raise to (i.e. the smallest you can increase your pip).
        max_amount: if BetAction or RaiseAction is valid, the largest amount you can bet or raise to (i.e. the largest you can increase your pip).
        '''

        if self.check_player and round.hand_num == 1:
            self.check_player = False
            if len(move_history) % 2 == 0:
                self.opp = 'B'
            else:
                self.opp = 'A'
            print("we think opponent is player " + self.opp)

    
        last_move = move_history[-1]
        if last_move == 'CHECK:' + self.opp:
            self.opp_check += 1
            # print(last_move + ", opponent check count = " + str(self.opp_check))
           

        if self.stop and FoldAction in legal_moves:
            return FoldAction()
        elif self.stop and CheckAction in legal_moves:
            return CheckAction()


        if round.hand_num==50:
            if self.fold_before_flop >15:
                self.opp_bluff_before_flop = True
                print("over 15 self.fold_before_flop")
            if self.fold_before_turn >20:
                self.opp_bluff_before_turn = True
                print("over 15 self.fold_before_turn")

            
        if calc is not None:
            result = calc(''.join(cards) + ':xx', ''.join(board_cards), ''.join(self.discarded_cards), 1000)
            if result is not None:
                strength = result.ev[0]
            else:
                print "Warning: calc returned None"
                strength = random.random()
        else:
            strength = random.random()
        #sophia 
        
        # anti bluff block

        if min_amount == 160:
            strength = 0.95
            if CallAction in legal_moves:
                return CallAction()

        
        if len(board_cards) == 5 and FoldAction in legal_moves:
            # check if last move was opponent bet
            last_move = move_history[-1]
            if "BET" in last_move and last_move[-1] == self.opp:
                if len(self.opp_river_bet) > 3:
                    if round.hand_num < 400:
                        best_fit = stats.linregress(np.array(self.opp_river_bet), np.array(self.opp_river_strength))
                        self.slope = best_fit[0]
                        self.intercept = best_fit[1]
                    
                    self.predicted_strength = min(1,int(last_move.split(':')[1])*self.slope + self.intercept)
                    print("slope = " + str(self.slope) + ", intercept = " + str(self.intercept))
                    print("predicted strength: " + str(self.predicted_strength))
                    print("our strength: " + str(strength))
                    if self.predicted_strength >= strength + 0.05:
                        print("folded bc opponent's bet indicates stronger")
                        if round.hand_num <= 20:
                            if min_amount <= 60:
                                self.fold += 1
                        return FoldAction()
        

        
        if ExchangeAction in legal_moves and self.exchange_count<3 and len(board_cards)>=3:  # decision to exchange
            # exchange logic
            # if we exchange, we should update self.discarded_cards
            exchange_cost = cost_func(ExchangeAction())
            exchange_ev = 0.6 * pot.opponent_total - 0.4 * (pot.total + exchange_cost)
            check_ev = strength * pot.opponent_total - (1. - strength) * pot.total
            if exchange_ev > check_ev and len(board_cards)>3 and strength <= 0.75:  # exchanging is worth it
                self.discarded_cards |= set(cards)  # keep track of the cards we discarded
                self.exchange_count +=1
                return ExchangeAction()
            return CheckAction()

        if self.fold >= 11 and len(board_cards) == 3 and min_amount <= 40:
            if CallAction in legal_moves:
                print("antibluff 1")
                return CallAction()
        if self.fold >= 11 and len(board_cards) == 4 and min_amount <= 50:
            if CallAction in legal_moves:
                print("antibluff 1")
                return CallAction()
        if self.fold >= 11 and len(board_cards) == 5 and min_amount <=60:
            if CallAction in legal_moves:
                print("antibluff 1")
                return CallAction()

        if len(board_cards)==0 and strength*0.5>random.random():
            if RaiseAction in legal_moves and min_amount<10:
                raise_amt = min_amount + 5 * (random.random())
                raise_amt = max(raise_amt, min_amount)
                raise_amt = min(raise_amt, max_amount)
                return RaiseAction(raise_amt)
        
        if len(board_cards)==3 and strength*0.5>random.random():
            if RaiseAction in legal_moves and min_amount<10:
                raise_amt = min_amount + 5 * (random.random())
                raise_amt = max(raise_amt, min_amount)
                raise_amt = min(raise_amt, max_amount)
                return RaiseAction(raise_amt)

      
        if not (ExchangeAction in legal_moves and self.exchange_count<3 and len(board_cards)>=3):  # decision to commit resources to the pot

            continue_cost = cost_func(CallAction()) if CallAction in legal_moves else cost_func(CheckAction())
            # figure out how to raise the stakes
            commit_amount=0
            if len(board_cards)==0:
                commit_amount = int(pot.pip + continue_cost + (strength*random.random()) * (pot.grand_total + continue_cost))
            elif len(board_cards)==3:
                commit_amount = int(pot.pip + continue_cost + (1.5*strength*random.random()) * (pot.grand_total + continue_cost))
            elif len(board_cards)==4: # should be between 0.5 and 0.75
                commit_amount = int(pot.pip + continue_cost + (2*strength*random.random()) * (pot.grand_total + continue_cost))
            elif len(board_cards)==5:
                commit_amount = int(pot.pip + continue_cost + (2.25*strength*random.random()) * (pot.grand_total + continue_cost))
            if min_amount is not None:
                commit_amount = max(commit_amount, min_amount)
                commit_amount = min(commit_amount, max_amount)


            if continue_cost==0:
                if BetAction in legal_moves and strength > 0.95 and len(board_cards)>=4:
                    commit_action = BetAction(max_amount)
                else:
                    commit_action = CheckAction()

            

            if continue_cost > 0:
                if len(board_cards)!=0: #1
                    self.num_of_bets +=1
                if self.num_of_bets == 2 and strength <0.9: #2
                    strength -=0.03
                if self.num_of_bets == 3 and strength <0.9: #3
                    strength -=0.05
                if continue_cost > 20 and strength < 1:  #4.1
                    strength -= 0.05 
                    if strength <0.8 and len(board_cards)>=4:  #4.2
                        strength -= 0.05
                if continue_cost> 50 and strength < 0.95: #5
                    strength -= 0.11
                if pot.opponent_num_exchanges >0: #6
                    strength -= 0.05
                if continue_cost < 5 and len(board_cards)==5: #7
                    strength += 0.1

                if continue_cost >0:
                    if RaiseAction in legal_moves and len(board_cards) == 5 and strength >= 0.95:
                        commit_action = RaiseAction(commit_amount)
                    elif CallAction in legal_moves:  # we are contemplating an all-in call
                        commit_action = CallAction()
                    else:  # only legal action
                        return CheckAction()

                pot_odds = float(continue_cost) / (pot.grand_total + continue_cost)+0.1
                if len(board_cards)==0 and strength >0.5:
                    return commit_action
                if strength >= pot_odds or (self.opp_bluff_before_turn and len(board_cards)==3) or ((len(board_cards)==0) and self.opp_bluff_before_flop):
                    if strength >= 0.7: # commit more sometimes
                        return commit_action
                    last_move = move_history[-1]
                    if 'BET' in last_move and len(board_cards) == 3 and last_move[-1] == self.opp:
                        if int(last_move.split(':')[1]) > 300 and FoldAction in legal_moves:
                            print(last_move)
                            print('sophia flop all in fold')
                            if round.hand_num <= 20:
                                if min_amount <= 60:
                                    self.fold += 1
                            return FoldAction()
                    return CallAction()
                else:  # staying in the game has negative EV
                    if round.hand_num <= 20:
                        if min_amount <= 60:
                            self.fold += 1
                            print("hand" + str(round.hand_num) + ": " + str(self.fold))
                    return FoldAction()
            
            elif continue_cost == 0:
                if len(board_cards)==3:
                    strength += 0.02
                if len(board_cards)==4:
                    strength += 0.05
                if len(board_cards)==5:
                    strength +=0.1
                if self.opp_check >= 3 and strength >0.6 and pot.grand_total >=10 and pot.grand_total <= 20:
                    return commit_action
                if self.opp_check >4:
                    strength +=0.1
                if strength >= 0.6 and BetAction in legal_moves or RaiseAction in legal_moves: # commit more sometimes
                    return commit_action
                elif BetAction in legal_moves or RaiseAction in legal_moves and random.random() < strength:  # balance bluffs with value bets
                    return commit_action
                return CheckAction()

        if self.fold >= 11 and len(board_cards) >= 3 and min_amount <= 40:
                if CallAction in legal_moves:
                    print("antibluff 2")
                    return CallAction()

        if CheckAction in legal_moves:
            return CheckAction()
        elif CallAction in legal_moves and strength >= 0.7:
            return CallAction()
        elif FoldAction in legal_moves:
            if round.hand_num <= 20:
                if min_amount <= 60:
                    self.fold += 1
                    print("hand" + str(round.hand_num) + ": " + str(self.fold))
            return FoldAction()
                


if __name__ == '__main__':
    args = parse_args()
    run_bot(Player(), args)
