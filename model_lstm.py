import tensorflow as tf
import tensorflow.contrib.rnn as rnn

from datetime import datetime
from read_data import read_data_sets


DATA_FOLDER = "MNIST_data/"

MAX_CHARACTERS = 31
ALPHABET_SIZE = 31
NUM_GENDERS = 3

EPOCHS = 30
BATCH_SIZE = 512

NUM_LAYERS = 2
NUM_HIDDEN = [256, 128]
CELL_TYPE = rnn.BasicLSTMCell
DROPOUT_RATE = 0.5
LEARNING_RATE = 0.001


def echo(*message):
    print("[{0}] ".format(datetime.now().time()), end="")
    print(*message)


def get_last_output_from_static_rnn(input_words, seq_length, rnn_cell):
    """Create RNN by means of tf.static_rnn() and return last output"""
    rnn_outputs, rnn_state = rnn.static_rnn(
        rnn_cell, tf.unstack(input_words, axis=1),
        sequence_length=seq_length, dtype=tf.float32
    )

    indices = tf.stack([
        tf.range(0, tf.shape(input_words)[0]),
        seq_length - 1
    ], axis=1)

    last = tf.gather_nd(tf.stack(rnn_outputs, axis=1), indices)

    return last


def get_last_output_from_dynamic_rnn(input_words, seq_length, rnn_cell):
    """Create RNN by means of tf.dynamic_rnn() and return last output"""
    rnn_outputs, rnn_state = tf.nn.dynamic_rnn(
        rnn_cell, input_words,
        sequence_length=seq_length,
        dtype=tf.float32
    )

    indices = tf.stack([
        tf.range(0, tf.shape(input_words)[0]),
        seq_length - 1
    ], axis=1)

    last = tf.gather_nd(rnn_outputs, indices)

    return last


# BUILDING GRAPH

echo("Creating placeholders...")

# setting up placeholders
xs = tf.placeholder(tf.float32, [None, MAX_CHARACTERS, ALPHABET_SIZE])
ys = tf.placeholder(tf.float32, [None, NUM_GENDERS])
seq = tf.placeholder(tf.int32, [None])
dropout = tf.placeholder(tf.float32)

echo("Creating cells...")

# setting up RNN cells
layers = []
for i in range(NUM_LAYERS):
    layer = CELL_TYPE(NUM_HIDDEN[i])
    if DROPOUT_RATE > 0.0:
        layer = rnn.DropoutWrapper(layer, output_keep_prob=1.0 - dropout)
    layers.append(layer)
if NUM_LAYERS > 1:
    cell = rnn.MultiRNNCell(layers)
else:
    cell = layers[0]

echo("Creating network...")

# fetching last output of the RNN
last_output = get_last_output_from_dynamic_rnn(xs, seq, cell)

# inference artifacts
logits = tf.contrib.layers.fully_connected(
    last_output, NUM_GENDERS, activation_fn=None
)

# evaluation artifacts
mistakes = tf.not_equal(tf.argmax(ys, 1), tf.argmax(logits, 1))
error = tf.reduce_mean(tf.cast(mistakes, tf.float32))

# training artifacts
loss = tf.losses.softmax_cross_entropy(ys, logits)
optimizer = tf.train.AdamOptimizer(LEARNING_RATE)

echo("Computing gradients...")

# minimization
train = optimizer.minimize(loss)


# PREPARING DATA

echo("Preparing data...")

# (download and) extract MNIST dataset
dataset = read_data_sets()

print()
echo("Training set:", dataset.train.words.shape[0])
echo("Validation set:", dataset.validation.words.shape[0])
echo("Testing set:", dataset.test.words.shape[0])
print()


# EXECUTING THE GRAPH

with tf.Session() as sess:
    echo("Initializing variables...")

    sess.run(tf.global_variables_initializer())
    sess.run(tf.local_variables_initializer())

    echo("Training...")
    print()

    steps_per_epoch = dataset.train.words.shape[0] // BATCH_SIZE

    for epoch in range(EPOCHS):
        for step in range(steps_per_epoch):
            batch_xs, batch_ys, seq_len = dataset.train.next_batch(BATCH_SIZE)

            _, l, e = sess.run([train, loss, error], feed_dict={
                xs: batch_xs,
                ys: batch_ys,
                seq: seq_len,
                dropout: DROPOUT_RATE
            })

            echo("Epoch", epoch, "Batch", step, "loss", l, "error", e * 100)

        val_error = sess.run(
            error,
            feed_dict={
                xs: dataset.validation.words,
                ys: dataset.validation.genders,
                seq: dataset.validation.seq_length,
                dropout: 0.0
            }
        )

        # print()
        echo('Epoch {:2d}  error {:3.2f}%'.format(
            epoch + 1,
            100 * val_error
        ))
        # print()

    test_error = sess.run(
        error,
        feed_dict={
            xs: dataset.test.words,
            ys: dataset.test.genders,
            seq: dataset.test.seq_length,
            dropout: 0.0
        }
    )

    print()
    echo("Test error {:3.2f}% ".format(
        100 * test_error
    ))
