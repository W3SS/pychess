from gi.repository import Gtk

from pychess.Utils.const import UNDOABLE_STATES, PRACTICE_GOAL_REACHED
from pychess.Utils.Cord import Cord
from pychess.Utils.LearnModel import learn2str, LESSON, PUZZLE
from pychess.perspectives.learn.PuzzlesPanel import start_puzzle_from
from pychess.perspectives.learn.EndgamesPanel import start_endgame_from
from pychess.perspectives.learn.LessonsPanel import start_lesson_from
from pychess.widgets import preferencesDialog

HINT, MOVE, RETRY, CONTINUE, NEXT = range(5)


css = """
@define-color info_fg_color rgb (181, 171, 156);
@define-color info_bg_color rgb (252, 252, 189);
@define-color question_fg_color rgb (97, 122, 214);
@define-color question_bg_color rgb (138, 173, 212);
@define-color error_fg_color rgb (235, 235, 235);
@define-color error_bg_color rgb (223, 56, 44);

.question {
    background-image: -gtk-gradient (linear, left top, left bottom,
                                     from (shade (@question_bg_color, 1.04)),
                                     to (shade (@question_bg_color, 0.96)));
    border-style: solid;
    border-width: 1px;

    color: @question_fg_color;

    border-color: shade (@question_bg_color, 0.8);
    border-bottom-color: shade (@question_bg_color, 0.75);

    box-shadow: inset 1px 0 shade (@question_bg_color, 1.08),
                inset -1px 0 shade (@question_bg_color, 1.08),
                inset 0 1px shade (@question_bg_color, 1.1),
                inset 0 -1px shade (@question_bg_color, 1.04);
}

.info {
    background-image: -gtk-gradient (linear, left top, left bottom,
                                     from (shade (@info_bg_color, 1.04)),
                                     to (shade (@info_bg_color, 0.96)));
    border-style: solid;
    border-width: 1px;

    color: @info_fg_color;

    border-color: shade (@info_bg_color, 0.8);
    border-bottom-color: shade (@info_bg_color, 0.75);

    box-shadow: inset 1px 0 shade (@info_bg_color, 1.08),
                inset -1px 0 shade (@info_bg_color, 1.08),
                inset 0 1px shade (@info_bg_color, 1.1),
                inset 0 -1px shade (@info_bg_color, 1.04);
}

.error {
    background-image: -gtk-gradient (linear, left top, left bottom,
                                     from (shade (@error_bg_color, 1.04)),
                                     to (shade (@error_bg_color, 0.96)));
    border-style: solid;
    border-width: 1px;

    color: @error_fg_color;

    border-color: shade (@error_bg_color, 0.8);
    border-bottom-color: shade (@error_bg_color, 0.75);

    box-shadow: inset 1px 0 shade (@error_bg_color, 1.08),
                inset -1px 0 shade (@error_bg_color, 1.08),
                inset 0 1px shade (@error_bg_color, 1.1),
                inset 0 -1px shade (@error_bg_color, 1.04);
}
"""


def add_provider(widget):
    screen = widget.get_screen()
    style = widget.get_style_context()
    provider = Gtk.CssProvider()
    provider.load_from_data(css.encode('utf-8'))
    style.add_provider_for_screen(screen, provider, Gtk.STYLE_PROVIDER_PRIORITY_USER)


class LearnInfoBar(Gtk.InfoBar):
    def __init__(self, gamemodel, boardcontrol, annotation_panel):
        Gtk.InfoBar.__init__(self)
        self.connect("realize", add_provider)

        self.content_area = self.get_content_area()
        self.action_area = self.get_action_area()

        self.gamemodel = gamemodel
        self.boardcontrol = boardcontrol
        self.boardview = boardcontrol.view
        self.annotation_panel = annotation_panel

        self.gamemodel.connect("game_changed", self.on_game_changed)
        self.gamemodel.connect("goal_checked", self.on_goal_checked)
        self.connect("response", self.on_response)

        self.your_turn()

    def clear(self):
        for item in self.content_area:
            self.content_area.remove(item)

        for item in self.action_area:
            self.action_area.remove(item)

    def your_turn(self, shown_board=None):
        self.clear()
        self.set_message_type(Gtk.MessageType.QUESTION)
        self.content_area.add(Gtk.Label(_("Your turn.")))
        self.add_button(_("Hint"), HINT)
        self.add_button(_("Best move"), MOVE)
        self.show_all()

    def get_next_puzzle(self):
        self.clear()
        self.set_message_type(Gtk.MessageType.INFO)
        if self.gamemodel.learn_type in(LESSON, PUZZLE) and self.gamemodel.current_index + 1 == self.gamemodel.game_count:
            self.content_area.add(Gtk.Label(_("Well done! %s completed." % learn2str[self.gamemodel.learn_type])))
        else:
            self.content_area.add(Gtk.Label(_("Well done!")))
            self.add_button(_("Next"), NEXT)
        self.show_all()
        preferencesDialog.SoundTab.playAction("puzzleSuccess")

        if self.gamemodel.learn_type == LESSON:
            self.gamemodel.solved = True

    def opp_turn(self):
        self.clear()
        self.set_message_type(Gtk.MessageType.INFO)
        self.add_button(_("Continue"), CONTINUE)

        # disable playing
        self.boardcontrol.game_preview = True
        self.show_all()

    def retry(self):
        self.clear()
        self.set_message_type(Gtk.MessageType.ERROR)
        self.content_area.add(Gtk.Label(_("Not the best move!")))
        self.add_button(_("Retry"), RETRY)

        # disable playing
        self.boardcontrol.game_preview = True

        # disable retry button until engine thinking on next move
        if self.gamemodel.practice_game:
            self.set_response_sensitive(RETRY, False)
        self.show_all()

    def on_response(self, widget, response):
        if response in (HINT, MOVE):
            if self.gamemodel.ply in self.gamemodel.hints:
                if self.boardview.arrows:
                    self.boardview.arrows.clear()
                if self.boardview.circles:
                    self.boardview.circles.clear()

                hint = self.gamemodel.hints[self.gamemodel.ply][0][0]
                cord0 = Cord(hint[0], int(hint[1]), "G")
                cord1 = Cord(hint[2], int(hint[3]), "G")
                if response == HINT:
                    self.boardview.circles.add(cord0)
                    self.boardview.redrawCanvas()
                else:
                    self.boardview.arrows.add((cord0, cord1))
                    self.boardview.redrawCanvas()
            else:
                # TODO:
                print("No hint available yet!")

        elif response == RETRY:
            self.your_turn()

            if self.gamemodel.practice_game:
                self.gamemodel.undoMoves(2)

            elif self.gamemodel.lesson_game:
                prev_board = self.gamemodel.getBoardAtPly(
                    self.boardview.shown - 1,
                    variation=self.boardview.shown_variation_idx)

                board = self.gamemodel.getBoardAtPly(
                    self.boardview.shown,
                    variation=self.boardview.shown_variation_idx)

                self.annotation_panel.choices_enabled = False
                self.boardview.setShownBoard(prev_board)
                # We have to fix show_variation_index here, unless
                # after removing the variation it will be invalid!
                for vari in self.gamemodel.variations:
                    if prev_board in vari:
                        break
                self.boardview.shown_variation_idx = self.gamemodel.variations.index(vari)

                self.annotation_panel.choices_enabled = True

                self.gamemodel.undo_in_variation(board)

            self.boardcontrol.game_preview = False

        elif response == CONTINUE:
            self.your_turn()
            self.boardview.showNext()
            self.boardcontrol.game_preview = False

        elif response == NEXT:
            if self.gamemodel.puzzle_game:
                start_puzzle_from(self.gamemodel.source, self.gamemodel.current_index + 1)
            elif self.gamemodel.end_game:
                start_endgame_from(self.gamemodel.source)
            elif self.gamemodel.lesson_game:
                start_lesson_from(self.gamemodel.source, self.gamemodel.current_index + 1)
            else:
                print(self.gamemodel.__dir__())

    def opp_choice_selected(self, board):
        self.your_turn()
        self.boardcontrol.game_preview = False

    def on_game_changed(self, gamemodel, ply):
        if gamemodel.practice_game:
            if len(gamemodel.moves) % 2 == 0:
                # engine moved, we can enable retry
                self.set_response_sensitive(RETRY, True)
                return

    def on_goal_checked(self, gamemodel):
        if gamemodel.status in UNDOABLE_STATES and self.gamemodel.end_game:
            self.get_next_puzzle()
        elif gamemodel.reason == PRACTICE_GOAL_REACHED:
            self.get_next_puzzle()
        elif gamemodel.failed_playing_best:
            self.retry()
        else:
            self.your_turn()
