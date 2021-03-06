from flask import Blueprint, render_template, session
from webapp.lib.stock_util import gen_monte_carlo_paths, stats_from_paths, compound
from webapp.lib.queries import all_accounts_sum
from webapp.forms import MonteCarloForm
import matplotlib.pyplot as plt
from matplotlib.backends.backend_agg import FigureCanvasAgg as FigureCanvas
from flask import make_response
import io
import numpy as np
import locale
from matplotlib.ticker import FuncFormatter

monte_carlo_blueprint = Blueprint(
    'monte_carlo',
    __name__,
    template_folder='../templates'
)


@monte_carlo_blueprint.route("/monte-carlo", methods=['GET', 'POST'])
def monte_carlo():
    form = MonteCarloForm()
    if form.rate.data is not None:
        rate = float(form.rate.data)
    else:
        rate = 0.07
    if form.sigma.data is not None:
        sigma = float(form.sigma.data)
    else:
        sigma = 0.15
    if form.time.data is not None:
        time = float(form.time.data)
    else:
        time = 10
    if form.start_val.data is not None:
        start_value = float(form.start_val.data)
    else:
        start_value = all_accounts_sum()
    if form.annual_contrib.data is not None:
        annual_contrib = float(form.annual_contrib.data)
    else:
        annual_contrib = 0
    paths = gen_monte_carlo_paths(start_value, r=rate, sigma=sigma, time=time, annual_contrib=annual_contrib)
    session['paths'] = paths[:, :20]
    session['final_prices'] = paths[-1]
    session['rate'] = rate
    session['time'] = time
    session['start_value'] = start_value
    session['annual_contrib'] = annual_contrib
    stats = stats_from_paths(paths)
    mean = locale.currency(paths[-1].mean(), grouping=True)
    return render_template("monte_carlo.html",
                           paths=paths,
                           stats=stats,
                           start_value=("{:.2f}".format(start_value)),
                           start_val_for=locale.currency(start_value, grouping=True),
                           rate=rate,
                           sigma=sigma,
                           time=time,
                           mean=mean,
                           annual_contrib=annual_contrib,
                           form=form)


@monte_carlo_blueprint.route("/monte-carlo/paths.png")
def path_chart():
    plt.close()
    plt.figure(figsize=(12,6))
    paths = session.pop('paths')
    plt.plot(paths[:, :20])
    compounded = compound(session.pop('start_value'), session.pop('rate'), session.pop('time'), session.pop('annual_contrib'))
    plt.plot(compounded, linewidth=5, color='black', alpha=.5)
    plt.grid(True)
    plt.xlabel('months')
    plt.ylabel('value')
    plt.title("Sample Simulation Paths")
    canvas = FigureCanvas(plt.gcf())
    png_output = io.BytesIO()
    canvas.print_png(png_output)
    response=make_response(png_output.getvalue())
    response.headers['Content-Type'] = 'image/png'
    return response


@monte_carlo_blueprint.route("/monte-carlo/histogram.png")
def histogram():

    plt.close()
    plt.figure(figsize=(12,6))
    final_prices = session.pop('final_prices')

    plt.hist(final_prices, bins=100)
    plt.title("Histogram")
    plt.ylabel('frequency')
    plt.xlabel('Final Value')
    plt.xlim(0, np.percentile(final_prices, 99.5))

    formatter = FuncFormatter(lambda y, p: str(100 * y / len(final_prices)) + '%')
    plt.gca().yaxis.set_major_formatter(formatter)

    formatter = FuncFormatter(lambda x, p: locale.format('%d',x, True))
    plt.gca().xaxis.set_major_formatter(formatter)

    canvas = FigureCanvas(plt.gcf())
    png_output = io.BytesIO()
    canvas.print_png(png_output)
    response = make_response(png_output.getvalue())
    response.headers['Content-Type'] = 'image/png'
    return response
