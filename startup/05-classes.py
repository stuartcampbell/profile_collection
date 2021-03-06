from bluesky.callbacks import LivePlot, _get_obj_fields
import matplotlib.pyplot as plt
import numpy as np

class LivePlotWithErrors(CallbackBase):
    """
    Build a function that updates a plot from a stream of Events.
    Note: If your figure blocks the main thread when you are trying to
    scan with this callback, call `plt.ion()` in your IPython session.
    Parameters
    ----------
    y : str
        the name of a data field in an Event
    x : str, optional
        the name of a data field in an Event
        If None, use the Event's sequence number.
    legend_keys : list, optional
        The list of keys to extract from the RunStart document and format
        in the legend of the plot. The legend will always show the
        scan_id followed by a colon ("1: ").  Each
    xlim : tuple, optional
        passed to Axes.set_xlim
    ylim : tuple, optional
        passed to Axes.set_ylim
    ax : Axes, optional
        matplotib Axes; if none specified, new figure and axes are made.
    fig : Figure
        deprecated: use ax instead
    All additional keyword arguments are passed through to ``Axes.plot``.
    Examples
    --------
    >>> my_plotter = LivePlot('det', 'motor', legend_keys=['sample'])
    >>> RE(my_scan, my_plotter)
    """
    def __init__(self, y, x=None, *, legend_keys=None, xlim=None, ylim=None,
                 ax=None, fig=None, **kwargs):
        super().__init__()
        if fig is not None:
            if ax is not None:
                raise ValueError("Values were given for both `fig` and `ax`. "
                                 "Only one can be used; prefer ax.")
            warnings.warn("The `fig` keyword arugment of LivePlot is "
                          "deprecated and will be removed in the future. "
                          "Instead, use the new keyword argument `ax` to "
                          "provide specific Axes to plot on.")
            ax = fig.gca()
        if ax is None:
            fig, ax = plt.subplots()
        self.ax = ax

        if legend_keys is None:
            legend_keys = []
        self.legend_keys = ['scan_id'] + legend_keys
        if x is not None:
            self.x, *others = _get_obj_fields([x])
        else:
            self.x = None
        self.y, *others = _get_obj_fields([y])
        self.ax.set_ylabel(y)
        self.ax.set_xlabel(x or 'sequence #')
        if xlim is not None:
            self.ax.set_xlim(*xlim)
        if ylim is not None:
            self.ax.set_ylim(*ylim)
        self.ax.margins(.1)
        self.kwargs = kwargs
        self.lines = []
        self.legend = None
        self.legend_title = " :: ".join([name for name in self.legend_keys])

    def start(self, doc):
        # The doc is not used; we just use the singal that a new run began.
        self.x_data, self.y_data = [], []
        self.e_data = []
        label = " :: ".join(
            [str(doc.get(name, name)) for name in self.legend_keys])
        kwargs = ChainMap(self.kwargs, {'label': label})
        #self.current_line, = self.ax.plot([], [], **kwargs)
        self.current_line = self.ax.errorbar([], [], yerr=[], **kwargs)
        self.lines.append(self.current_line)
        #self.legend = self.ax.legend(
        #    loc=0, title=self.legend_title).draggable()
        super().start(doc)

    def event(self, doc):
        "Unpack data from the event and call self.update()."
        try:
            if self.x is not None:
                # this try/except block is needed because multiple event
                # streams will be emitted by the RunEngine and not all event
                # streams will have the keys we want
                new_x = doc['data'][self.x]
            else:
                new_x = doc['seq_num']
            new_y = doc['data'][self.y]
        except KeyError:
            # wrong event stream, skip it
            return
        self.update_caches(new_x, new_y)
        self.update_plot()
        super().event(doc)

    def update_caches(self, x, y):
        self.y_data.append(y)
        self.x_data.append(x)
        self.e_data.append(np.sqrt(y))

    def update_plot(self):

        # For now (as in for the HYSPEC test) I am just going to do something nasty
        # and just plot everytime!
        self.current_line = self.ax.errorbar(self.x_data, self.y_data, yerr=self.e_data)

        #
        # try:
        #     line, (bottoms, tops), verts = self.current_line
        #     line.set_xdata(self.x_data)
        #     line.set_ydata(self.y_data)
        #     bottoms.set_xdata(self.x_data)
        #     bottoms.set_ydata(self.y_data - self.e_data)
        #     tops.set_xdata(self.x_data)
        #     tops.set_ydaya(self.y_data + self.e_data)
        #     # TODO: Still need to do something with the verts ?
        # except:
        #     # If there 'verts' was None, then there was nothing plotted, for
        #     # now lets just do an initial plot.
        #     self.current_line = self.ax.errorbar(self.x_data, self.y_data, yerr=self.e_data)

        #
        #
        # yerr_top = self.y_data + self.e_data
        # yerr_bot = self.y_data - self.e_data
        # erry_top.set_xdata(self.x_data)
        # erry_bot.set_xdata(self.x_data)
        # erry_top.set_ydata(yerr_top)
        # erry_bot.set_ydata(yerr_bot)
        #
        # new_segments_y = [np.array([[x, yt], [x,yb]]) for x, yt, yb in
        #             zip(self.x_data, yerr_top, yerr_bot)]
        #
        # barsy.set_segments(new_segments_y)

        # Rescale and redraw.
        self.ax.relim(visible_only=True)
        self.ax.autoscale_view(tight=True)
        self.ax.figure.canvas.draw_idle()

    def stop(self, doc):
        if not self.x_data:
            print('LivePlot did not get any data that corresponds to the '
                  'x axis. {}'.format(self.x))
        if not self.y_data:
            print('LivePlot did not get any data that corresponds to the '
                  'y axis. {}'.format(self.y))
        if len(self.y_data) != len(self.x_data):
            print('LivePlot has a different number of elements for x ({}) and'
                  'y ({})'.format(len(self.x_data), len(self.y_data)))
        super().stop(doc)
