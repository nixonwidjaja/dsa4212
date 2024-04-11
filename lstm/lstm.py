import jax
import jax.numpy as jnp
from utils import RANDOM_SEED, rng_normal, sigmoid, LSTMParams, \
    LSTMModelParams, LSTMArchiParams

class LSTM:
    @staticmethod
    def init_params(
        seed: int,
        input_dim: int,
        hidden_dim: int,
        output_dim: int
    ) -> tuple[LSTMArchiParams, LSTMParams]:
        key = jax.random.PRNGKey(seed)
        wf = rng_normal(key=key, shape=(hidden_dim, input_dim))
        uf = rng_normal(key=key, shape=(hidden_dim, hidden_dim))
        bf = rng_normal(key=key, shape=(hidden_dim, 1))
        wi = rng_normal(key=key, shape=(hidden_dim, input_dim))
        ui = rng_normal(key=key, shape=(hidden_dim, hidden_dim))
        bi = rng_normal(key=key, shape=(hidden_dim, 1))
        wc = rng_normal(key=key, shape=(hidden_dim, input_dim))
        uc = rng_normal(key=key, shape=(hidden_dim, hidden_dim))
        bc = rng_normal(key=key, shape=(hidden_dim, 1))
        wo = rng_normal(key=key, shape=(hidden_dim, input_dim))
        uo = rng_normal(key=key, shape=(hidden_dim, hidden_dim))
        bo = rng_normal(key=key, shape=(hidden_dim, 1))
        wout = rng_normal(key=key, shape=(output_dim, hidden_dim))
        return LSTMArchiParams(key, input_dim, hidden_dim, output_dim), \
            LSTMParams(wf, uf, bf, wi, ui, bi, wc, uc, bc, wo, uo, bo, wout)

    @staticmethod
    @jax.jit
    def f_cur(
        params: LSTMParams, 
        x_cur: jnp.ndarray, 
        h_prev: jnp.ndarray
    ) -> jnp.ndarray:
        return sigmoid((params.uf @ h_prev) + (params.wf @ x_cur) + params.bf)
    
    @staticmethod
    @jax.jit
    def i_cur(
        params: LSTMParams, 
        x_cur: jnp.ndarray, 
        h_prev: jnp.ndarray
    ) -> jnp.ndarray:
        return sigmoid((params.ui @ h_prev) + (params.wi @ x_cur) + params.bi)

    @staticmethod
    @jax.jit
    def c_cur_hat(
        params: LSTMParams,
        x_cur: jnp.ndarray,
        h_prev: jnp.ndarray
    ) -> jnp.ndarray:
        return jnp.tanh((params.uc @ h_prev) + (params.wc @ x_cur) + params.bc)

    @staticmethod
    @jax.jit
    def c_cur(
        params: LSTMParams, 
        x_cur: jnp.ndarray, 
        h_prev: jnp.ndarray, 
        c_prev: jnp.ndarray
    ) -> jnp.ndarray:
        i_t = LSTM.i_cur(params, x_cur, h_prev)
        c_t_hat = LSTM.c_cur_hat(params, x_cur, h_prev)
        f_t = LSTM.f_cur(params, x_cur, h_prev)
        return f_t * c_prev + i_t * c_t_hat
        
    
    @staticmethod
    @jax.jit
    def o_cur(
        params: LSTMParams, 
        x_cur: jnp.ndarray, 
        h_prev: jnp.ndarray
    ) -> jnp.ndarray:
        return sigmoid(params.uo @ h_prev + params.wo @ x_cur + params.bo)
    
    @staticmethod
    @jax.jit
    def h_cur(
        params: LSTMParams, 
        x_cur: jnp.ndarray, 
        h_prev: jnp.ndarray, 
        c_prev: jnp.ndarray
    ) -> jnp.ndarray:
        o_t = LSTM.o_cur(params, x_cur, h_prev)
        c_t = LSTM.c_cur(params, x_cur, h_prev, c_prev)
        return o_t * jnp.tanh(c_t), c_t
        
    @staticmethod
    def forward(
        tup: tuple[jnp.ndarray, jnp.ndarray, jnp.ndarray],
        x_cur: jnp.ndarray
    ) -> tuple[jnp.ndarray, jnp.ndarray, jnp.ndarray]:
        params, h_prev, c_prev = tup
        h_t, c_t = LSTM.h_cur(params, x_cur, h_prev, c_prev)
        out_t = params.wout @ h_t
        return (params, h_t, c_t), out_t

    @staticmethod
    def forward_full(
        archi_params: LSTMArchiParams,
        params: LSTMParams, 
        x_in: jnp.ndarray
    ) -> jnp.ndarray:
        h, c = jnp.zeros(shape=(archi_params.hidden_dim, 1)), jnp.zeros(shape=(archi_params.hidden_dim, 1))
        (params, h, c), out_ls = jax.lax.scan(LSTM.forward, (params, h, c), x_in[0])
        return out_ls
    
    @staticmethod
    def forward_batch(
        archi_params: LSTMArchiParams,
        params: LSTMParams,
        x_batch: jnp.ndarray
    ) -> jnp.ndarray:
        forward_full_batch = jax.vmap(LSTM.forward_full, in_axes=(None, None, 0))
        return jnp.squeeze(forward_full_batch(archi_params, params, x_batch), axis=3)
    
    @staticmethod
    def mse(
        archi_params: LSTMArchiParams,
        params: LSTMParams,
        x_batch: jnp.ndarray,
        y_batch: jnp.ndarray
    ) -> jnp.ndarray:
        batch_out = LSTM.forward_batch(archi_params, params, x_batch)
        return jnp.mean((batch_out - y_batch) ** 2)
    
    @staticmethod
    def backward(
        archi_params: LSTMArchiParams,
        params: LSTMParams,
        x_batch: jnp.ndarray,
        y_batch: jnp.ndarray
    ) -> jnp.ndarray:
        mse_grad = jax.jacfwd(LSTM.mse, argnums=(1,))
        cur_grad = mse_grad(archi_params, params, x_batch, y_batch)
        return cur_grad

class PeepholeLSTM(LSTM):
    @staticmethod
    @jax.jit
    def f_cur(
        params: LSTMParams, 
        x_cur: jnp.ndarray, 
        h_prev: jnp.ndarray, 
        c_prev: jnp.ndarray
    ) -> jnp.ndarray:
        return sigmoid(params.wf @ jnp.concatenate([c_prev, h_prev, x_cur], axis=0) + params.bf)

    @staticmethod
    @jax.jit
    def i_cur(
        params: LSTMParams, 
        x_cur: jnp.ndarray, 
        h_prev: jnp.ndarray, 
        c_prev: jnp.ndarray
    ) -> jnp.ndarray:
        return sigmoid(params.wi @ jnp.concatenate([c_prev, h_prev, x_cur], axis=0) + params.bi)
    
    @staticmethod
    @jax.jit
    def o_cur(
        params: LSTMParams, 
        x_cur: jnp.ndarray, 
        h_prev: jnp.ndarray, 
        c_cur: jnp.ndarray
    ) -> jnp.ndarray:
        return sigmoid(params.wo @ jnp.concatenate([c_cur, h_prev, x_cur], axis=0) + params.bo)

    @staticmethod
    @jax.jit
    def h_cur(
        params: LSTMParams, 
        x_cur: jnp.ndarray, 
        h_prev: jnp.ndarray, 
        c_prev: jnp.ndarray, 
        c_t: jnp.ndarray
    ) -> jnp.ndarray:
        return PeepholeLSTM.o_cur(params, x_cur, h_prev, c_t) * jnp.tanh(PeepholeLSTM.c_cur(params, x_cur, h_prev, c_prev))

    @staticmethod
    @jax.jit
    def forward(
        params: LSTMParams,
        x_cur: jnp.ndarray, 
        h_prev: jnp.ndarray, 
        c_prev: jnp.ndarray,
        wout: jnp.ndarray
    ) -> tuple[jnp.ndarray, jnp.ndarray, jnp.ndarray]:
        c_t = PeepholeLSTM.c_cur(params, x_cur, h_prev, c_prev)
        h_t = PeepholeLSTM.h_cur(params, x_cur, h_prev, c_prev, c_t)
        o_t = wout @ h_t
        return (c_t, o_t, h_t)

    @staticmethod
    def forward_full(
        params: LSTMParams, 
        x_in: jnp.ndarray
    ) -> jnp.ndarray:
        time_steps = x_in.shape[1]
        h, o, c = jnp.zeros(shape=(params.hidden_dim, 1)), jnp.zeros(shape=(params.output_dim, 1)), \
            jnp.zeros(shape=(params.hidden_dim, 1))
        o_ls = []
        for i in range(time_steps):
            if len(x_in.shape) == 1:
                c_t, o_t, h_t = LSTM.forward(params, x_in[i:i+1], h, c, params.wout)
            elif len(x_in.shape) == 2:
                c_t, o_t, h_t = LSTM.forward(params, x_in[:,i:i+1], h, c, params.wout)
            elif len(x_in.shape) == 3:
                c_t, o_t, h_t = LSTM.forward(params, x_in[:,i:i+1,:], h, c, params.wout) 
            o_ls.append(o_t)
            h, o, c = h_t, o_t, c_t
        return jnp.array(o_ls)

    @staticmethod
    def forward_batch(
        params: LSTMParams,
        x_batch: jnp.ndarray
    ) -> jnp.ndarray:
        forward_full_batch = jax.vmap(LSTM.forward_full, in_axes=(None, 0))
        return jnp.squeeze(forward_full_batch(params, x_batch), axis=3)
    
    @staticmethod
    def mse(
        params: LSTMParams,
        x_batch: jnp.ndarray,
        y_batch: jnp.ndarray
    ) -> tuple[jnp.ndarray, jnp.ndarray]:
        batch_out = LSTM.forward_batch(params, x_batch)
        return jnp.mean((batch_out - y_batch) ** 2) * 100
    
    @staticmethod
    def backward(
        params: LSTMParams,
        x_batch: jnp.ndarray,
        y_batch: jnp.ndarray
    ) -> tuple[jnp.ndarray, jnp.ndarray]:
        mse_grad = jax.jacobian(LSTM.mse, argnums=(0,), allow_int=True)
        cur_grad = mse_grad(params, x_batch, y_batch)
        return cur_grad

class LSTMModel:
    def init_params(
        input_dim: int,
        hidden_dim: int,
        output_dim: int,
        num_lstm: int,
        lstm_type: str,
        seed: int = RANDOM_SEED
    ):
        assert num_lstm >= 1, "num_lstm must be >= 1"
        if (lstm_type == "vanilla"):
            layers = [LSTM.init_params(
                seed=seed, 
                input_dim=input_dim, 
                hidden_dim=hidden_dim,
                output_dim=output_dim
            ) 
                for _ in range(num_lstm)]
        elif (lstm_type == "peephole"):
            layers = [PeepholeLSTM.init_params(
                seed=seed,
                input_dim=input_dim, 
                hidden_dim=hidden_dim,
                output_dim=output_dim
            )
                for _ in range(num_lstm)]
        else:
            raise ValueError("lstm_type must be 'vanilla' or 'peephole'.")
        return LSTMModelParams(num_lstm, lstm_type, layers)

    def forward(params: LSTMModelParams, x_in: jnp.ndarray) -> jnp.ndarray:
        num_lstm = params.num_lstm
        o_out = jnp.zeros(shape=(x_in.shape[0], params.layers[0].output_dim))
        for i in range(num_lstm):
            cur_params = params.layers[i]
            o_out = type(params.layers[0]).forward_full(cur_params, x_in)
        return o_out
        