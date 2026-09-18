"""
Generates data/aiml_curriculum.json containing 17 curated, mathematically rigorous
AI/ML & Data Engineering interview problems with verified starter code, reference
solutions, test cases, and parameter specifications.
"""
import json
import math
import os
import sys

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data")
OUTPUT_FILE = os.path.join(DATA_DIR, "aiml_curriculum.json")

def generate_curriculum():
    problems = []

    # =========================================================================
    # PILLAR 1: GENERATIVE AI & TRANSFORMERS
    # =========================================================================

    # 1. Scaled Dot-Product Attention
    problems.append({
        "id": "step_18_scaled_dot_product_attention",
        "title": "Scaled Dot-Product Attention",
        "step": "Step 18 - AI/ML & Data Engineering",
        "topic": "Transformers & LLMs",
        "difficulty": "Medium",
        "method_name": "scaled_dot_product_attention",
        "description": (
            "### Scaled Dot-Product Attention\n\n"
            "Scaled Dot-Product Attention is the foundational computational core of Transformer architectures "
            "(Vaswani et al., 2017) powering modern LLMs such as **GPT-4, Claude 3.5, and Gemini**.\n\n"
            "#### Mathematical Formulation\n"
            "Given Query matrix $Q \\in \\mathbb{R}^{S \\times d_k}$, Key matrix $K \\in \\mathbb{R}^{S \\times d_k}$, and Value matrix $V \\in \\mathbb{R}^{S \\times d_v}$:\n"
            "$$\\text{Attention}(Q, K, V) = \\text{softmax}\\left(\\frac{QK^T}{\\sqrt{d_k}} + M\\right)V$$\n\n"
            "Where:\n"
            "- $QK^T$ computes similarity scores between all token pairs.\n"
            "- $\\frac{1}{\\sqrt{d_k}}$ scales dot products to prevent softmax gradients from vanishing for large dimensions.\n"
            "- $M$ is an optional additive attention mask (e.g. causal mask with $-\\infty$ or $-1e9$ for future tokens).\n"
            "- $\\text{softmax}$ normalizes scores across each row so weights sum to $1.0$.\n\n"
            "#### Requirements\n"
            "Implement `scaled_dot_product_attention(Q, K, V, mask=None)` in pure Python without PyTorch.\n"
            "- Inputs $Q, K, V$ are 2D lists of floats of shape `(S, d_k)` (and `(S, d_v)` for $V$).\n"
            "- `mask` is optional: if provided, a 2D list of shape `(S, S)` with `0.0` or `-1e9`.\n"
            "- Return a 2D list of shape `(S, d_v)` representing the context-weighted values."
        ),
        "parameters": [
            {"name": "Q", "type": "List[List[float]]", "description": "Query matrix of shape (S, d_k)"},
            {"name": "K", "type": "List[List[float]]", "description": "Key matrix of shape (S, d_k)"},
            {"name": "V", "type": "List[List[float]]", "description": "Value matrix of shape (S, d_v)"},
            {"name": "mask", "type": "Optional[List[List[float]]]", "description": "Optional additive mask of shape (S, S)"},
        ],
        "return_type": "List[List[float]]",
        "constraints": [
            "1 <= S (sequence length) <= 64",
            "1 <= d_k, d_v <= 64",
            "All float values are finite within [-1e4, 1e4]",
            "Outputs compared within absolute tolerance 1e-4",
        ],
        "starter_code": (
            "from typing import List, Optional\n"
            "import math\n\n"
            "class Solution:\n"
            "    def scaled_dot_product_attention(\n"
            "        self,\n"
            "        Q: List[List[float]],\n"
            "        K: List[List[float]],\n"
            "        V: List[List[float]],\n"
            "        mask: Optional[List[List[float]]] = None\n"
            "    ) -> List[List[float]]:\n"
            "        # Write your attention implementation here\n"
            "        pass\n"
        ),
        "reference_solution": (
            "from typing import List, Optional\n"
            "import math\n\n"
            "class Solution:\n"
            "    def scaled_dot_product_attention(\n"
            "        self,\n"
            "        Q: List[List[float]],\n"
            "        K: List[List[float]],\n"
            "        V: List[List[float]],\n"
            "        mask: Optional[List[List[float]]] = None\n"
            "    ) -> List[List[float]]:\n"
            "        S = len(Q)\n"
            "        d_k = len(Q[0])\n"
            "        d_v = len(V[0])\n"
            "        scale = math.sqrt(d_k)\n\n"
            "        # 1. Compute scores = (Q @ K.T) / sqrt(d_k)\n"
            "        scores = []\n"
            "        for i in range(S):\n"
            "            row = []\n"
            "            for j in range(S):\n"
            "                dot = sum(Q[i][d] * K[j][d] for d in range(d_k))\n"
            "                val = dot / scale\n"
            "                if mask is not None and mask[i][j] != 0:\n"
            "                    val += mask[i][j]\n"
            "                row.append(val)\n"
            "            scores.append(row)\n\n"
            "        # 2. Softmax per row with numerical stability max subtraction\n"
            "        weights = []\n"
            "        for row in scores:\n"
            "            max_val = max(row)\n"
            "            exp_row = [math.exp(x - max_val) for x in row]\n"
            "            sum_exp = sum(exp_row)\n"
            "            weights.append([x / sum_exp for x in exp_row])\n\n"
            "        # 3. Output = weights @ V\n"
            "        output = []\n"
            "        for i in range(S):\n"
            "            out_row = []\n"
            "            for j in range(d_v):\n"
            "                out_val = sum(weights[i][k] * V[k][j] for k in range(S))\n"
            "                out_row.append(round(out_val, 6))\n"
            "            output.append(out_row)\n\n"
            "        return output\n"
        ),
        "test_cases": [
            {
                "input": [[[1.0, 0.0], [0.0, 1.0]], [[1.0, 0.0], [0.0, 1.0]], [[1.0, 2.0], [3.0, 4.0]]],
                "expected": [[1.660477, 2.660477], [2.339523, 3.339523]],
                "description": "2x2 identity queries and keys with values",
            },
            {
                "input": [[[1.0, 0.0], [0.0, 1.0]], [[1.0, 0.0], [0.0, 1.0]], [[1.0, 2.0], [3.0, 4.0]], [[0.0, -1e9], [0.0, 0.0]]],
                "expected": [[1.0, 2.0], [2.339523, 3.339523]],
                "description": "2x2 with causal mask blocking token 0 attending to token 1",
            }
        ]
    })

    # 2. RMSNorm (Root Mean Square Layer Normalization)
    problems.append({
        "id": "step_18_rmsnorm",
        "title": "RMSNorm (Root Mean Square Layer Normalization)",
        "step": "Step 18 - AI/ML & Data Engineering",
        "topic": "Transformers & LLMs",
        "difficulty": "Easy",
        "method_name": "rmsnorm",
        "description": (
            "### RMSNorm (Root Mean Square Layer Normalization)\n\n"
            "RMSNorm (Zhang & Sennrich, 2019) is an efficient alternative to traditional LayerNorm used in "
            "state-of-the-art open models including **LLaMA 1/2/3, Mistral, and DeepSeek-V3**.\n\n"
            "Traditional LayerNorm normalizes both mean and variance. RMSNorm hypothesizes that the re-centering "
            "step (mean subtraction) is unnecessary, and normalizes only by the root mean square (RMS) of activations, "
            "saving 7% to 15% wall-clock latency while preserving identical modeling quality.\n\n"
            "#### Mathematical Formulation\n"
            "$$\\text{RMS}(x) = \\sqrt{\\frac{1}{d}\\sum_{i=1}^d x_i^2 + \\epsilon}$$\n"
            "$$\\bar{x}_i = \\frac{x_i}{\\text{RMS}(x)} \\cdot \\gamma_i$$\n\n"
            "#### Requirements\n"
            "Implement `rmsnorm(x, gamma, eps=1e-6)` where:\n"
            "- `x`: 1D list of floats of dimension $d$.\n"
            "- `gamma`: 1D list of learned gain weights of dimension $d$.\n"
            "- `eps`: small constant to prevent division by zero (default `1e-6`).\n"
            "- Return the normalized 1D list of floats."
        ),
        "parameters": [
            {"name": "x", "type": "List[float]", "description": "Input activation vector of size d"},
            {"name": "gamma", "type": "List[float]", "description": "Scale parameter vector of size d"},
            {"name": "eps", "type": "float", "description": "Epsilon for numerical stability (default 1e-6)"},
        ],
        "return_type": "List[float]",
        "constraints": [
            "1 <= d <= 512",
            "-1e3 <= x[i], gamma[i] <= 1e3",
            "Absolute tolerance 1e-4",
        ],
        "starter_code": (
            "from typing import List\n"
            "import math\n\n"
            "class Solution:\n"
            "    def rmsnorm(self, x: List[float], gamma: List[float], eps: float = 1e-6) -> List[float]:\n"
            "        # Write your RMSNorm implementation here\n"
            "        pass\n"
        ),
        "reference_solution": (
            "from typing import List\n"
            "import math\n\n"
            "class Solution:\n"
            "    def rmsnorm(self, x: List[float], gamma: List[float], eps: float = 1e-6) -> List[float]:\n"
            "        d = len(x)\n"
            "        mean_sq = sum(val * val for val in x) / d\n"
            "        rms = math.sqrt(mean_sq + eps)\n"
            "        return [round((val / rms) * g, 6) for val, g in zip(x, gamma)]\n"
        ),
        "test_cases": [
            {
                "input": [[1.0, 2.0, 3.0, 4.0], [1.0, 1.0, 1.0, 1.0], 1e-6],
                "expected": [0.365148, 0.730297, 1.095445, 1.460593],
                "description": "Simple 4-element vector with unit gamma",
            },
            {
                "input": [[2.0, 2.0, 2.0], [0.5, 1.0, 2.0], 1e-6],
                "expected": [0.5, 1.0, 2.0],
                "description": "Uniform vector with varying scale weights",
            }
        ]
    })

    # 3. Byte-Pair Encoding (BPE) Tokenizer
    problems.append({
        "id": "step_18_bpe_tokenizer",
        "title": "Byte-Pair Encoding (BPE) Tokenizer Merge",
        "step": "Step 18 - AI/ML & Data Engineering",
        "topic": "Transformers & LLMs",
        "difficulty": "Medium",
        "method_name": "bpe_merge",
        "description": (
            "### Byte-Pair Encoding (BPE) Tokenizer Merge\n\n"
            "Byte-Pair Encoding (Sennrich et al., 2016) is the subword tokenization algorithm used by **GPT-2, "
            "GPT-4 (tiktoken), and LLaMA** to convert raw text into token IDs without out-of-vocabulary (OOV) errors.\n\n"
            "#### Algorithm\n"
            "Given a list of words represented as lists of characters/symbols:\n"
            "1. Count frequencies of all adjacent symbol pairs across all words.\n"
            "2. Identify the most frequent pair `(A, B)` (break ties by lexicographical order `(A, B)`).\n"
            "3. Merge all occurrences of `(A, B)` into a single new symbol `'AB'`.\n"
            "4. Repeat for $k$ iterations or until no adjacent pair has frequency $> 1$.\n\n"
            "#### Requirements\n"
            "Implement `bpe_merge(corpus, num_merges)` where:\n"
            "- `corpus`: list of strings (e.g. `['low', 'lower', 'newest', 'widest']`).\n"
            "- `num_merges`: number of BPE merge iterations.\n"
            "- Return the merged tokenized representation for each word as a list of lists of strings."
        ),
        "parameters": [
            {"name": "corpus", "type": "List[str]", "description": "List of words to tokenize"},
            {"name": "num_merges", "type": "int", "description": "Number of top-pair merges to execute"},
        ],
        "return_type": "List[List[str]]",
        "constraints": [
            "1 <= len(corpus) <= 100",
            "1 <= len(word) <= 30",
            "1 <= num_merges <= 50",
        ],
        "starter_code": (
            "from typing import List\n"
            "from collections import Counter\n\n"
            "class Solution:\n"
            "    def bpe_merge(self, corpus: List[str], num_merges: int) -> List[List[str]]:\n"
            "        # Write your BPE implementation here\n"
            "        pass\n"
        ),
        "reference_solution": (
            "from typing import List\n"
            "from collections import Counter\n\n"
            "class Solution:\n"
            "    def bpe_merge(self, corpus: List[str], num_merges: int) -> List[List[str]]:\n"
            "        # Tokenize each word into list of characters + end-of-word symbol\n"
            "        words = [list(w) for w in corpus]\n\n"
            "        for _ in range(num_merges):\n"
            "            pairs = Counter()\n"
            "            for w in words:\n"
            "                for i in range(len(w) - 1):\n"
            "                    pairs[(w[i], w[i + 1])] += 1\n\n"
            "            if not pairs:\n"
            "                break\n\n"
            "            # Most frequent pair, tie-breaking by alphabetical pair\n"
            "            best_pair = max(pairs.keys(), key=lambda p: (pairs[p], -ord(p[0][0]) if p[0] else 0))\n"
            "            if pairs[best_pair] < 1:\n"
            "                break\n\n"
            "            target_p0, target_p1 = best_pair\n"
            "            merged_symbol = target_p0 + target_p1\n\n"
            "            # Merge in words\n"
            "            new_words = []\n"
            "            for w in words:\n"
            "                new_w = []\n"
            "                i = 0\n"
            "                while i < len(w):\n"
            "                    if i < len(w) - 1 and w[i] == target_p0 and w[i + 1] == target_p1:\n"
            "                        new_w.append(merged_symbol)\n"
            "                        i += 2\n"
            "                    else:\n"
            "                        new_w.append(w[i])\n"
            "                        i += 1\n"
            "                new_words.append(new_w)\n"
            "            words = new_words\n\n"
            "        return words\n"
        ),
        "test_cases": [
            {
                "input": [["low", "low", "low"], 2],
                "expected": [["low"], ["low"], ["low"]],
                "description": "Repeated word 'low' merged into single subword",
            },
            {
                "input": [["aa", "ab", "ba"], 1],
                "expected": [["aa"], ["a", "b"], ["b", "a"]],
                "description": "Single merge on most frequent bigram 'aa'",
            }
        ]
    })

    # 4. Multi-Head Attention (MHA)
    problems.append({
        "id": "step_18_multi_head_attention",
        "title": "Multi-Head Attention (MHA) Projection & Split",
        "step": "Step 18 - AI/ML & Data Engineering",
        "topic": "Transformers & LLMs",
        "difficulty": "Hard",
        "method_name": "multi_head_split",
        "description": (
            "### Multi-Head Attention (MHA) Projection & Head Splitting\n\n"
            "Multi-Head Attention allows Transformer models to jointly attend to information from different "
            "representation subspaces at different positions. A common interview question at OpenAI and Anthropic "
            "tests candidate ability to implement tensor reshapes and multi-head split operations without PyTorch.\n\n"
            "#### Requirements\n"
            "Given a 2D tensor `X` of shape `(S, d_model)` representing input sequence embeddings, and number of heads `H`:\n"
            "1. Verify $d_{model}$ is divisible by $H$. If not, return `[]`.\n"
            "2. Compute head dimension $d_{head} = d_{model} / H$.\n"
            "3. Split `X` into $H$ separate 2D matrices, each of shape `(S, d_{head})`.\n"
            "4. Return a 3D list of shape `(H, S, d_{head})`."
        ),
        "parameters": [
            {"name": "X", "type": "List[List[float]]", "description": "Input sequence matrix of shape (S, d_model)"},
            {"name": "H", "type": "int", "description": "Number of attention heads"},
        ],
        "return_type": "List[List[List[float]]]",
        "constraints": [
            "1 <= S <= 64",
            "1 <= d_model <= 256",
            "1 <= H <= 16",
        ],
        "starter_code": (
            "from typing import List\n\n"
            "class Solution:\n"
            "    def multi_head_split(self, X: List[List[float]], H: int) -> List[List[List[float]]]:\n"
            "        # Write your MHA split implementation here\n"
            "        pass\n"
        ),
        "reference_solution": (
            "from typing import List\n\n"
            "class Solution:\n"
            "    def multi_head_split(self, X: List[List[float]], H: int) -> List[List[List[float]]]:\n"
            "        if not X or not X[0]:\n"
            "            return []\n"
            "        S = len(X)\n"
            "        d_model = len(X[0])\n"
            "        if d_model % H != 0:\n"
            "            return []\n\n"
            "        d_head = d_model // H\n"
            "        heads = [[] for _ in range(H)]\n\n"
            "        for h in range(H):\n"
            "            head_mat = []\n"
            "            start_col = h * d_head\n"
            "            end_col = start_col + d_head\n"
            "            for row in X:\n"
            "                head_mat.append(row[start_col:end_col])\n"
            "            heads[h] = head_mat\n\n"
            "        return heads\n"
        ),
        "test_cases": [
            {
                "input": [[[1.0, 2.0, 3.0, 4.0], [5.0, 6.0, 7.0, 8.0]], 2],
                "expected": [
                    [[1.0, 2.0], [5.0, 6.0]],
                    [[3.0, 4.0], [7.0, 8.0]]
                ],
                "description": "2 sequence tokens with d_model=4 split across 2 heads of d_head=2",
            },
            {
                "input": [[[1.0, 2.0, 3.0]], 2],
                "expected": [],
                "description": "d_model=3 not divisible by H=2 returns empty list",
            }
        ]
    })

    # 5. Rotary Position Embeddings (RoPE)
    problems.append({
        "id": "step_18_rope",
        "title": "Rotary Position Embeddings (RoPE)",
        "step": "Step 18 - AI/ML & Data Engineering",
        "topic": "Transformers & LLMs",
        "difficulty": "Hard",
        "method_name": "apply_rope",
        "description": (
            "### Rotary Position Embedding (RoPE)\n\n"
            "Rotary Position Embedding (Su et al., 2021) encodes relative positional information by multiplying "
            "Query and Key vectors with an orthogonal rotation matrix. It powers **LLaMA, Mistral, Gemma, and DeepSeek**.\n\n"
            "#### 2D Formulation\n"
            "For each adjacent coordinate pair $(x_{2i}, x_{2i+1})$ of a vector at sequence position $m$:\n"
            "$$\\theta_i = 10000^{-2i/d}$$\n"
            "$$\\begin{pmatrix} x'_{2i} \\\\ x'_{2i+1} \\end{pmatrix} = \\begin{pmatrix} \\cos(m\\theta_i) & -\\sin(m\\theta_i) \\\\ \\sin(m\\theta_i) & \\cos(m\\theta_i) \\end{pmatrix} \\begin{pmatrix} x_{2i} \\\\ x_{2i+1} \\end{pmatrix}$$\n\n"
            "#### Requirements\n"
            "Implement `apply_rope(x, pos)` where:\n"
            "- `x`: 1D list of floats of even length $d$.\n"
            "- `pos`: integer sequence index $m$.\n"
            "- Return the rotated 1D list of floats."
        ),
        "parameters": [
            {"name": "x", "type": "List[float]", "description": "Feature vector of even dimension d"},
            {"name": "pos", "type": "int", "description": "Token position index m (0-indexed)"},
        ],
        "return_type": "List[float]",
        "constraints": [
            "2 <= len(x) <= 128 (len(x) is even)",
            "0 <= pos <= 1024",
            "Tolerance 1e-4",
        ],
        "starter_code": (
            "from typing import List\n"
            "import math\n\n"
            "class Solution:\n"
            "    def apply_rope(self, x: List[float], pos: int) -> List[float]:\n"
            "        # Write your RoPE implementation here\n"
            "        pass\n"
        ),
        "reference_solution": (
            "from typing import List\n"
            "import math\n\n"
            "class Solution:\n"
            "    def apply_rope(self, x: List[float], pos: int) -> List[float]:\n"
            "        d = len(x)\n"
            "        out = [0.0] * d\n"
            "        for i in range(0, d, 2):\n"
            "            idx = i // 2\n"
            "            theta = 1.0 / (10000.0 ** (2 * idx / d))\n"
            "            angle = pos * theta\n"
            "            c = math.cos(angle)\n"
            "            s = math.sin(angle)\n"
            "            x0, x1 = x[i], x[i + 1]\n"
            "            out[i] = round(x0 * c - x1 * s, 6)\n"
            "            out[i + 1] = round(x0 * s + x1 * c, 6)\n"
            "        return out\n"
        ),
        "test_cases": [
            {
                "input": [[1.0, 0.0], 0],
                "expected": [1.0, 0.0],
                "description": "Position 0 with zero rotation angle returns original vector",
            },
            {
                "input": [[1.0, 0.0], 1],
                "expected": [0.540302, 0.841471],
                "description": "Position 1 rotated by theta_0 = 1.0 radian (cos(1)=0.5403, sin(1)=0.8414)",
            }
        ]
    })

    # 6. Sinusoidal Positional Encoding
    problems.append({
        "id": "step_18_sinusoidal_positional_encoding",
        "title": "Sinusoidal Positional Encoding",
        "step": "Step 18 - AI/ML & Data Engineering",
        "topic": "Transformers & LLMs",
        "difficulty": "Easy",
        "method_name": "get_positional_encoding",
        "description": (
            "### Sinusoidal Positional Encoding\n\n"
            "In *Attention Is All You Need* (Vaswani et al., 2017), since Transformer self-attention is permutation-invariant, "
            "deterministic sinusoidal wave functions of different frequencies are added to input embeddings.\n\n"
            "#### Mathematical Formulation\n"
            "$$PE_{(pos, 2i)} = \\sin\\left(\\frac{pos}{10000^{2i/d}}\\right)$$\n"
            "$$PE_{(pos, 2i+1)} = \\cos\\left(\\frac{pos}{10000^{2i/d}}\\right)$$\n\n"
            "#### Requirements\n"
            "Implement `get_positional_encoding(seq_len, d_model)` returning a 2D list of shape `(seq_len, d_model)`."
        ),
        "parameters": [
            {"name": "seq_len", "type": "int", "description": "Length of input sequence (number of positions)"},
            {"name": "d_model", "type": "int", "description": "Embedding dimension (must be even)"},
        ],
        "return_type": "List[List[float]]",
        "constraints": [
            "1 <= seq_len <= 64",
            "2 <= d_model <= 64 (even integer)",
        ],
        "starter_code": (
            "from typing import List\n"
            "import math\n\n"
            "class Solution:\n"
            "    def get_positional_encoding(self, seq_len: int, d_model: int) -> List[List[float]]:\n"
            "        # Write your positional encoding here\n"
            "        pass\n"
        ),
        "reference_solution": (
            "from typing import List\n"
            "import math\n\n"
            "class Solution:\n"
            "    def get_positional_encoding(self, seq_len: int, d_model: int) -> List[List[float]]:\n"
            "        pe = []\n"
            "        for pos in range(seq_len):\n"
            "            row = [0.0] * d_model\n"
            "            for i in range(0, d_model, 2):\n"
            "                denom = 10000.0 ** (i / d_model)\n"
            "                row[i] = round(math.sin(pos / denom), 6)\n"
            "                row[i + 1] = round(math.cos(pos / denom), 6)\n"
            "            pe.append(row)\n"
            "        return pe\n"
        ),
        "test_cases": [
            {
                "input": [2, 4],
                "expected": [
                    [0.0, 1.0, 0.0, 1.0],
                    [0.841471, 0.540302, 0.00999997, 0.99995]
                ],
                "description": "2 positions with d_model=4",
            }
        ]
    })

    # =========================================================================
    # PILLAR 2: CLASSICAL MACHINE LEARNING & OPTIMIZATION
    # =========================================================================

    # 7. K-Means Clustering
    problems.append({
        "id": "step_18_kmeans_clustering",
        "title": "K-Means Clustering from Scratch",
        "step": "Step 18 - AI/ML & Data Engineering",
        "topic": "Machine Learning Algorithms",
        "difficulty": "Medium",
        "method_name": "kmeans",
        "description": (
            "### K-Means Clustering\n\n"
            "Implement Lloyd's algorithm for **K-Means Clustering** in pure Python.\n\n"
            "#### Algorithm\n"
            "Given a list of 2D data points and initial centroids:\n"
            "1. **Assignment Step**: Assign each point to the closest centroid using squared Euclidean distance.\n"
            "   $$d(x, c) = \\sum_{j=1}^D (x_j - c_j)^2$$\n"
            "2. **Update Step**: Recalculate each centroid as the arithmetic mean of all points assigned to its cluster.\n"
            "   If a cluster has no assigned points, its centroid remains unchanged.\n"
            "3. Repeat for `max_iters` iterations or until centroids converge (no change).\n\n"
            "#### Requirements\n"
            "Implement `kmeans(points, initial_centroids, max_iters)` returning the final list of centroids."
        ),
        "parameters": [
            {"name": "points", "type": "List[List[float]]", "description": "N data points of dimension D"},
            {"name": "initial_centroids", "type": "List[List[float]]", "description": "K starting cluster centroids"},
            {"name": "max_iters", "type": "int", "description": "Maximum iterations to execute"},
        ],
        "return_type": "List[List[float]]",
        "constraints": [
            "1 <= N <= 200",
            "1 <= K <= 10",
            "1 <= max_iters <= 100",
        ],
        "starter_code": (
            "from typing import List\n\n"
            "class Solution:\n"
            "    def kmeans(self, points: List[List[float]], initial_centroids: List[List[float]], max_iters: int) -> List[List[float]]:\n"
            "        # Write your K-Means implementation here\n"
            "        pass\n"
        ),
        "reference_solution": (
            "from typing import List\n\n"
            "class Solution:\n"
            "    def kmeans(self, points: List[List[float]], initial_centroids: List[List[float]], max_iters: int) -> List[List[float]]:\n"
            "        centroids = [list(c) for c in initial_centroids]\n"
            "        K = len(centroids)\n"
            "        D = len(points[0]) if points else 0\n\n"
            "        for _ in range(max_iters):\n"
            "            clusters = [[] for _ in range(K)]\n"
            "            for p in points:\n"
            "                best_k = 0\n"
            "                min_dist = float('inf')\n"
            "                for k in range(K):\n"
            "                    dist = sum((p[d] - centroids[k][d]) ** 2 for d in range(D))\n"
            "                    if dist < min_dist:\n"
            "                        min_dist = dist\n"
            "                        best_k = k\n"
            "                clusters[best_k].append(p)\n\n"
            "            new_centroids = []\n"
            "            for k in range(K):\n"
            "                if not clusters[k]:\n"
            "                    new_centroids.append(centroids[k])\n"
            "                else:\n"
            "                    mean_c = [round(sum(pt[d] for pt in clusters[k]) / len(clusters[k]), 4) for d in range(D)]\n"
            "                    new_centroids.append(mean_c)\n\n"
            "            if new_centroids == centroids:\n"
            "                break\n"
            "            centroids = new_centroids\n\n"
            "        return centroids\n"
        ),
        "test_cases": [
            {
                "input": [[[1.0, 1.0], [1.5, 2.0], [8.0, 8.0], [9.0, 9.0]], [[0.0, 0.0], [10.0, 10.0]], 10],
                "expected": [[1.25, 1.5], [8.5, 8.5]],
                "description": "Two distinct clusters converging cleanly",
            }
        ]
    })

    # 8. Numerically Stable Softmax & Cross-Entropy
    problems.append({
        "id": "step_18_stable_softmax",
        "title": "Numerically Stable Softmax & Cross-Entropy Loss",
        "step": "Step 18 - AI/ML & Data Engineering",
        "topic": "Machine Learning Algorithms",
        "difficulty": "Easy",
        "method_name": "stable_softmax_cross_entropy",
        "description": (
            "### Numerically Stable Softmax & Cross-Entropy Loss\n\n"
            "A classic deep learning interview trap at Google & Meta: computing $e^z$ directly overflows 64-bit floats "
            "when $z > 709$. To ensure numerical stability, implement the **Log-Sum-Exp trick** by subtracting $\\max(z)$.\n\n"
            "#### Formulation\n"
            "$$\\text{softmax}(z)_i = \\frac{e^{z_i - \\max(z)}}{\\sum_j e^{z_j - \\max(z)}}$$\n"
            "$$\\text{CrossEntropy}(p, y) = -\\log(p_y + 1e-15)$$\n\n"
            "#### Requirements\n"
            "Implement `stable_softmax_cross_entropy(logits, target_class)` returning `[probabilities, loss]`."
        ),
        "parameters": [
            {"name": "logits", "type": "List[float]", "description": "Unnormalized model prediction scores"},
            {"name": "target_class", "type": "int", "description": "Ground truth class index (0-indexed)"},
        ],
        "return_type": "List[Any]",
        "constraints": [
            "2 <= len(logits) <= 1000",
            "0 <= target_class < len(logits)",
            "Logits may contain extreme values like 1000.0 without overflowing",
        ],
        "starter_code": (
            "from typing import List, Tuple, Any\n"
            "import math\n\n"
            "class Solution:\n"
            "    def stable_softmax_cross_entropy(self, logits: List[float], target_class: int) -> List[Any]:\n"
            "        # Write your stable softmax implementation here\n"
            "        pass\n"
        ),
        "reference_solution": (
            "from typing import List, Any\n"
            "import math\n\n"
            "class Solution:\n"
            "    def stable_softmax_cross_entropy(self, logits: List[float], target_class: int) -> List[Any]:\n"
            "        max_l = max(logits)\n"
            "        exp_l = [math.exp(x - max_l) for x in logits]\n"
            "        sum_exp = sum(exp_l)\n"
            "        probs = [round(x / sum_exp, 6) for x in exp_l]\n"
            "        loss = round(-math.log(max(probs[target_class], 1e-15)), 6)\n"
            "        return [probs, loss]\n"
        ),
        "test_cases": [
            {
                "input": [[1000.0, 1001.0, 1002.0], 2],
                "expected": [[0.090031, 0.244728, 0.665241], 0.407604],
                "description": "Extreme logits that would overflow naive exp() evaluate stably",
            }
        ]
    })

    # 9. Dense Layer Forward & Backward Pass (Backpropagation)
    problems.append({
        "id": "step_18_dense_layer_backprop",
        "title": "Dense Layer Forward & Backward Pass (Backpropagation)",
        "step": "Step 18 - AI/ML & Data Engineering",
        "topic": "Machine Learning Algorithms",
        "difficulty": "Hard",
        "method_name": "dense_forward_backward",
        "description": (
            "### Dense Layer Forward & Backward Pass\n\n"
            "Implement the fundamental building block of Neural Network Backpropagation (Rumelhart et al., 1986).\n\n"
            "#### Equations\n"
            "1. **Forward Pass**: $Z = XW + b$\n"
            "2. **Backward Pass** (given upstream gradient $\\frac{\\partial L}{\\partial Z}$):\n"
            "   $$\\frac{\\partial L}{\\partial W} = X^T \\frac{\\partial L}{\\partial Z}$$\n"
            "   $$\\frac{\\partial L}{\\partial b} = \\sum_{\\text{rows}} \\frac{\\partial L}{\\partial Z}$$\n"
            "   $$\\frac{\\partial L}{\\partial X} = \\frac{\\partial L}{\\partial Z} W^T$$\n\n"
            "#### Requirements\n"
            "Implement `dense_forward_backward(X, W, b, dZ)` returning `[dW, db, dX]`."
        ),
        "parameters": [
            {"name": "X", "type": "List[List[float]]", "description": "Input activations of shape (N, D_in)"},
            {"name": "W", "type": "List[List[float]]", "description": "Weight matrix of shape (D_in, D_out)"},
            {"name": "b", "type": "List[float]", "description": "Bias vector of length D_out"},
            {"name": "dZ", "type": "List[List[float]]", "description": "Upstream gradient of shape (N, D_out)"},
        ],
        "return_type": "List[Any]",
        "constraints": [
            "1 <= N <= 32, 1 <= D_in, D_out <= 32",
        ],
        "starter_code": (
            "from typing import List, Any\n\n"
            "class Solution:\n"
            "    def dense_forward_backward(\n"
            "        self,\n"
            "        X: List[List[float]],\n"
            "        W: List[List[float]],\n"
            "        b: List[float],\n"
            "        dZ: List[List[float]]\n"
            "    ) -> List[Any]:\n"
            "        # Write your forward/backward pass here\n"
            "        pass\n"
        ),
        "reference_solution": (
            "from typing import List, Any\n\n"
            "class Solution:\n"
            "    def dense_forward_backward(\n"
            "        self,\n"
            "        X: List[List[float]],\n"
            "        W: List[List[float]],\n"
            "        b: List[float],\n"
            "        dZ: List[List[float]]\n"
            "    ) -> List[Any]:\n"
            "        N = len(X)\n"
            "        D_in = len(W)\n"
            "        D_out = len(b)\n\n"
            "        # dW = X^T @ dZ of shape (D_in, D_out)\n"
            "        dW = []\n"
            "        for i in range(D_in):\n"
            "            row = []\n"
            "            for j in range(D_out):\n"
            "                val = sum(X[n][i] * dZ[n][j] for n in range(N))\n"
            "                row.append(round(val, 4))\n"
            "            dW.append(row)\n\n"
            "        # db = sum(dZ, axis=0) of length D_out\n"
            "        db = [round(sum(dZ[n][j] for n in range(N)), 4) for j in range(D_out)]\n\n"
            "        # dX = dZ @ W^T of shape (N, D_in)\n"
            "        dX = []\n"
            "        for n in range(N):\n"
            "            row = []\n"
            "            for i in range(D_in):\n"
            "                val = sum(dZ[n][j] * W[i][j] for j in range(D_out))\n"
            "                row.append(round(val, 4))\n"
            "            dX.append(row)\n\n"
            "        return [dW, db, dX]\n"
        ),
        "test_cases": [
            {
                "input": [
                    [[1.0, 2.0]],
                    [[0.5, 0.2], [0.1, 0.4]],
                    [0.0, 0.0],
                    [[1.0, 1.0]]
                ],
                "expected": [
                    [[1.0, 1.0], [2.0, 2.0]],
                    [1.0, 1.0],
                    [[0.7, 0.5]]
                ],
                "description": "1x2 input through 2x2 layer backprop",
            }
        ]
    })

    # 10. Linear Regression via Gradient Descent
    problems.append({
        "id": "step_18_linear_regression_gd",
        "title": "Linear Regression via Gradient Descent",
        "step": "Step 18 - AI/ML & Data Engineering",
        "topic": "Machine Learning Algorithms",
        "difficulty": "Medium",
        "method_name": "train_linear_regression",
        "description": (
            "### Vectorized Linear Regression via Gradient Descent\n\n"
            "Fit a single-variable linear model $\\hat{y} = w x + b$ minimizing Mean Squared Error (MSE):\n"
            "$$J(w, b) = \\frac{1}{2N} \\sum_{i=1}^N (\\hat{y}_i - y_i)^2$$\n\n"
            "#### Gradient Updates\n"
            "$$\\frac{\\partial J}{\\partial w} = \\frac{1}{N} \\sum (\\hat{y}_i - y_i) x_i, \\quad \\frac{\\partial J}{\\partial b} = \\frac{1}{N} \\sum (\\hat{y}_i - y_i)$$\n"
            "$$w := w - \\alpha \\frac{\\partial J}{\\partial w}, \\quad b := b - \\alpha \\frac{\\partial J}{\\partial b}$$\n\n"
            "#### Requirements\n"
            "Implement `train_linear_regression(x, y, lr, epochs)` returning `[final_w, final_b]` initialized at `w=0.0, b=0.0`."
        ),
        "parameters": [
            {"name": "x", "type": "List[float]", "description": "Independent variable samples"},
            {"name": "y", "type": "List[float]", "description": "Target dependent variable values"},
            {"name": "lr", "type": "float", "description": "Learning rate alpha"},
            {"name": "epochs", "type": "int", "description": "Number of training iterations"},
        ],
        "return_type": "List[float]",
        "constraints": [
            "2 <= len(x) == len(y) <= 500",
            "1 <= epochs <= 1000",
        ],
        "starter_code": (
            "from typing import List\n\n"
            "class Solution:\n"
            "    def train_linear_regression(self, x: List[float], y: List[float], lr: float, epochs: int) -> List[float]:\n"
            "        # Write your gradient descent training loop here\n"
            "        pass\n"
        ),
        "reference_solution": (
            "from typing import List\n\n"
            "class Solution:\n"
            "    def train_linear_regression(self, x: List[float], y: List[float], lr: float, epochs: int) -> List[float]:\n"
            "        w = 0.0\n"
            "        b = 0.0\n"
            "        N = len(x)\n\n"
            "        for _ in range(epochs):\n"
            "            dw = 0.0\n"
            "            db = 0.0\n"
            "            for xi, yi in zip(x, y):\n"
            "                pred = w * xi + b\n"
            "                err = pred - yi\n"
            "                dw += err * xi\n"
            "                db += err\n"
            "            w -= lr * (dw / N)\n"
            "            b -= lr * (db / N)\n\n"
            "        return [round(w, 4), round(b, 4)]\n"
        ),
        "test_cases": [
            {
                "input": [[1.0, 2.0, 3.0, 4.0], [2.0, 4.0, 6.0, 8.0], 0.05, 500],
                "expected": [1.9952, 0.0142],
                "description": "Exact y = 2x line learning slope ~2.0",
            }
        ]
    })

    # =========================================================================
    # PILLAR 3: DATA ENGINEERING & STREAMING
    # =========================================================================

    # 11. Sliding Window Stream Aggregator
    problems.append({
        "id": "step_18_sliding_window_aggregator",
        "title": "Sliding Window Stream Aggregator",
        "step": "Step 18 - AI/ML & Data Engineering",
        "topic": "Data Engineering & Streaming",
        "difficulty": "Medium",
        "method_name": "sliding_window_avg",
        "description": (
            "### Sliding Window Stream Aggregator\n\n"
            "In streaming architectures (Apache Flink, Spark Streaming, Kafka), metrics must be calculated "
            "over a sliding time duration $W$.\n\n"
            "#### Requirements\n"
            "Given a stream of timestamped events `(timestamp_sec, value)` sorted chronologically by timestamp, "
            "compute the moving average of values occurring within the last $W$ seconds for each event (inclusive).\n"
            "- Formula: $\\text{avg} = \\frac{\\sum_{\\{v \\mid t - W < t_i \\le t\\}} v_i}{\\text{count}}$\n"
            "- Return a list of floats representing the moving average at each event."
        ),
        "parameters": [
            {"name": "events", "type": "List[List[float]]", "description": "List of [timestamp, value] pairs"},
            {"name": "window_size", "type": "float", "description": "Duration W of the sliding window"},
        ],
        "return_type": "List[float]",
        "constraints": [
            "1 <= len(events) <= 1000",
            "Events are sorted in non-decreasing order of timestamps",
        ],
        "starter_code": (
            "from typing import List\n"
            "from collections import deque\n\n"
            "class Solution:\n"
            "    def sliding_window_avg(self, events: List[List[float]], window_size: float) -> List[float]:\n"
            "        # Write your sliding window aggregator here\n"
            "        pass\n"
        ),
        "reference_solution": (
            "from typing import List\n"
            "from collections import deque\n\n"
            "class Solution:\n"
            "    def sliding_window_avg(self, events: List[List[float]], window_size: float) -> List[float]:\n"
            "        dq = deque()\n"
            "        running_sum = 0.0\n"
            "        averages = []\n\n"
            "        for t, val in events:\n"
            "            dq.append((t, val))\n"
            "            running_sum += val\n\n"
            "            # Evict out-of-window elements\n"
            "            while dq and (t - dq[0][0]) >= window_size:\n"
            "                old_t, old_val = dq.popleft()\n"
            "                running_sum -= old_val\n\n"
            "            averages.append(round(running_sum / len(dq), 4))\n\n"
            "        return averages\n"
        ),
        "test_cases": [
            {
                "input": [[[1.0, 10.0], [2.0, 20.0], [3.0, 30.0], [5.0, 40.0]], 3.0],
                "expected": [10.0, 15.0, 20.0, 35.0],
                "description": "Window size 3.0 evicts t=1.0 when at t=5.0",
            }
        ]
    })

    # 12. Reservoir Sampling
    problems.append({
        "id": "step_18_reservoir_sampling",
        "title": "Reservoir Sampling (Uniform Streaming)",
        "step": "Step 18 - AI/ML & Data Engineering",
        "topic": "Data Engineering & Streaming",
        "difficulty": "Easy",
        "method_name": "reservoir_sample",
        "description": (
            "### Reservoir Sampling (Algorithm R)\n\n"
            "A standard interview question at Databricks, Google, and Snowflake: select $k$ items with uniform probability "
            "$\\frac{1}{N}$ from an infinite stream where total count $N$ is unknown beforehand.\n\n"
            "#### Algorithm\n"
            "1. Put the first $k$ items into the reservoir.\n"
            "2. For each subsequent item $i$ (from $k$ to $N-1$):\n"
            "   - Pick a pseudo-random integer $j \\in [0, i]$.\n"
            "   - If $j < k$, replace `reservoir[j]` with `stream[i]`.\n\n"
            "#### Requirements\n"
            "Implement `reservoir_sample(stream, k, random_indices)` where `random_indices` is a pre-seeded "
            "list of deterministic replacement decisions for testing."
        ),
        "parameters": [
            {"name": "stream", "type": "List[int]", "description": "Stream of elements"},
            {"name": "k", "type": "int", "description": "Reservoir capacity"},
            {"name": "random_indices", "type": "List[int]", "description": "Deterministic index choices for elements from k onward"},
        ],
        "return_type": "List[int]",
        "constraints": [
            "1 <= k <= len(stream) <= 1000",
        ],
        "starter_code": (
            "from typing import List\n\n"
            "class Solution:\n"
            "    def reservoir_sample(self, stream: List[int], k: int, random_indices: List[int]) -> List[int]:\n"
            "        # Write your reservoir sampling implementation here\n"
            "        pass\n"
        ),
        "reference_solution": (
            "from typing import List\n\n"
            "class Solution:\n"
            "    def reservoir_sample(self, stream: List[int], k: int, random_indices: List[int]) -> List[int]:\n"
            "        reservoir = list(stream[:k])\n"
            "        for i in range(k, len(stream)):\n"
            "            idx_in_rand = i - k\n"
            "            j = random_indices[idx_in_rand] if idx_in_rand < len(random_indices) else k + 1\n"
            "            if j < k:\n"
            "                reservoir[j] = stream[i]\n"
            "        return reservoir\n"
        ),
        "test_cases": [
            {
                "input": [[1, 2, 3, 4, 5], 3, [1, 5]],
                "expected": [1, 4, 3],
                "description": "k=3 reservoir with replacement at index 1 for item 4, no replacement for item 5",
            }
        ]
    })

    # 13. In-Memory MapReduce Engine
    problems.append({
        "id": "step_18_mapreduce_engine",
        "title": "In-Memory MapReduce Pipeline",
        "step": "Step 18 - AI/ML & Data Engineering",
        "topic": "Data Engineering & Streaming",
        "difficulty": "Medium",
        "method_name": "map_reduce_word_count",
        "description": (
            "### In-Memory MapReduce Pipeline\n\n"
            "Implement the core 3-stage MapReduce distributed computing pattern (Dean & Ghemawat, Google 2004):\n"
            "1. **Map Stage**: Map each document to key-value pairs `(word, 1)` (case-insensitive words).\n"
            "2. **Shuffle / Group Stage**: Group values by key into `(word, [1, 1, ...])`.\n"
            "3. **Reduce Stage**: Aggregate counts to produce final `(word, total_count)`.\n\n"
            "#### Requirements\n"
            "Implement `map_reduce_word_count(documents)` returning dictionary mapping each unique lowercase word to its count."
        ),
        "parameters": [
            {"name": "documents", "type": "List[str]", "description": "List of text documents"},
        ],
        "return_type": "Dict[str, int]",
        "constraints": [
            "1 <= len(documents) <= 200",
            "Words delimited by spaces and alphanumeric",
        ],
        "starter_code": (
            "from typing import List, Dict\n\n"
            "class Solution:\n"
            "    def map_reduce_word_count(self, documents: List[str]) -> Dict[str, int]:\n"
            "        # Write your MapReduce pipeline here\n"
            "        pass\n"
        ),
        "reference_solution": (
            "from typing import List, Dict\n"
            "from collections import defaultdict\n\n"
            "class Solution:\n"
            "    def map_reduce_word_count(self, documents: List[str]) -> Dict[str, int]:\n"
            "        # 1. Map Phase\n"
            "        intermediate = []\n"
            "        for doc in documents:\n"
            "            for word in doc.lower().split():\n"
            "                clean_w = ''.join(ch for ch in word if ch.isalnum())\n"
            "                if clean_w:\n"
            "                    intermediate.append((clean_w, 1))\n\n"
            "        # 2. Shuffle & Group Phase\n"
            "        groups = defaultdict(list)\n"
            "        for k, v in intermediate:\n"
            "            groups[k].append(v)\n\n"
            "        # 3. Reduce Phase\n"
            "        output = {}\n"
            "        for k in sorted(groups.keys()):\n"
            "            output[k] = sum(groups[k])\n\n"
            "        return output\n"
        ),
        "test_cases": [
            {
                "input": [["Hello world", "Hello DSA Nexus", "world of DSA"]],
                "expected": {"dsa": 2, "hello": 2, "nexus": 1, "of": 1, "world": 2},
                "description": "Multi-document word counting",
            }
        ]
    })

    # 14. Event Deduplication with Watermark Delay
    problems.append({
        "id": "step_18_stream_dedup_watermark",
        "title": "Stream Deduplication with Watermark Delay",
        "step": "Step 18 - AI/ML & Data Engineering",
        "topic": "Data Engineering & Streaming",
        "difficulty": "Medium",
        "method_name": "deduplicate_stream",
        "description": (
            "### Stream Deduplication with Watermark Delay\n\n"
            "Distributed stream processors (Kafka, Apache Flink) often receive duplicate events due to network retries. "
            "However, tracking all seen IDs forever causes infinite memory growth. A **Watermark Delay** specifies "
            "how long duplicate tracking state is retained.\n\n"
            "#### Requirements\n"
            "Given a stream of events `[event_id, timestamp]`, filter out duplicates:\n"
            "- An event is a duplicate if its `event_id` has already been seen within `timestamp - watermark_delay`.\n"
            "- If an event arrives with timestamp strictly less than `current_max_timestamp - watermark_delay`, it is dropped as late-arriving.\n"
            "- Return the list of accepted `event_id`s in order of emission."
        ),
        "parameters": [
            {"name": "events", "type": "List[List[Any]]", "description": "List of [event_id, timestamp] pairs"},
            {"name": "watermark_delay", "type": "float", "description": "Allowed out-of-order latency threshold"},
        ],
        "return_type": "List[str]",
        "constraints": [
            "1 <= len(events) <= 500",
        ],
        "starter_code": (
            "from typing import List, Any\n\n"
            "class Solution:\n"
            "    def deduplicate_stream(self, events: List[List[Any]], watermark_delay: float) -> List[str]:\n"
            "        # Write your watermark deduplicator here\n"
            "        pass\n"
        ),
        "reference_solution": (
            "from typing import List, Any\n\n"
            "class Solution:\n"
            "    def deduplicate_stream(self, events: List[List[Any]], watermark_delay: float) -> List[str]:\n"
            "        accepted = []\n"
            "        seen_ids = {}\n"
            "        max_time = 0.0\n\n"
            "        for eid, t in events:\n"
            "            if t > max_time:\n"
            "                max_time = t\n"
            "            watermark = max_time - watermark_delay\n\n"
            "            # Drop too-late events\n"
            "            if t < watermark:\n"
            "                continue\n\n"
            "            # Check if duplicate in window\n"
            "            if eid in seen_ids and (t - seen_ids[eid]) <= watermark_delay:\n"
            "                continue\n\n"
            "            seen_ids[eid] = t\n"
            "            accepted.append(str(eid))\n\n"
            "        return accepted\n"
        ),
        "test_cases": [
            {
                "input": [[["A", 10.0], ["B", 12.0], ["A", 13.0], ["C", 25.0], ["A", 30.0]], 5.0],
                "expected": ["A", "B", "C", "A"],
                "description": "Event A at t=13 is dropped as duplicate of t=10 (within 5.0s window), but A at t=30 is accepted",
            }
        ]
    })

    # 15. Logistic Regression with Sigmoid
    problems.append({
        "id": "step_18_logistic_regression",
        "title": "Logistic Regression with Sigmoid",
        "step": "Step 18 - AI/ML & Data Engineering",
        "topic": "Machine Learning Algorithms",
        "difficulty": "Medium",
        "method_name": "predict_probabilities",
        "description": (
            "### Logistic Regression with Sigmoid Activation\n\n"
            "Compute probability predictions for binary classification given feature vectors, weights, and bias.\n\n"
            "#### Mathematical Formulation\n"
            "$$z = X w + b$$\n"
            "$$\\sigma(z) = \\frac{1}{1 + e^{-z}}$$\n\n"
            "#### Requirements\n"
            "Implement `predict_probabilities(X, w, b)` returning 1D list of predicted probabilities $\\sigma(z_i)$."
        ),
        "parameters": [
            {"name": "X", "type": "List[List[float]]", "description": "N samples of dimension D"},
            {"name": "w", "type": "List[float]", "description": "Weight vector of length D"},
            {"name": "b", "type": "float", "description": "Scalar bias term"},
        ],
        "return_type": "List[float]",
        "constraints": [
            "1 <= N <= 200, 1 <= D <= 50",
            "Absolute tolerance 1e-4",
        ],
        "starter_code": (
            "from typing import List\n"
            "import math\n\n"
            "class Solution:\n"
            "    def predict_probabilities(self, X: List[List[float]], w: List[float], b: float) -> List[float]:\n"
            "        # Write your logistic regression prediction here\n"
            "        pass\n"
        ),
        "reference_solution": (
            "from typing import List\n"
            "import math\n\n"
            "class Solution:\n"
            "    def predict_probabilities(self, X: List[List[float]], w: List[float], b: float) -> List[float]:\n"
            "        probs = []\n"
            "        for row in X:\n"
            "            z = sum(x_i * w_i for x_i, w_i in zip(row, w)) + b\n"
            "            # Clip z for numerical stability\n"
            "            z_clipped = max(-50.0, min(50.0, z))\n"
            "            sig = 1.0 / (1.0 + math.exp(-z_clipped))\n"
            "            probs.append(round(sig, 4))\n"
            "        return probs\n"
        ),
        "test_cases": [
            {
                "input": [[[1.0, 2.0], [-1.0, -2.0], [0.0, 0.0]], [1.0, 1.0], 0.0],
                "expected": [0.9526, 0.0474, 0.5],
                "description": "Positive z gives >0.5, negative gives <0.5, zero gives 0.5",
            }
        ]
    })

    # 16. Top-K Frequent Stream Elements
    problems.append({
        "id": "step_18_top_k_stream",
        "title": "Top-K Frequent Stream Elements",
        "step": "Step 18 - AI/ML & Data Engineering",
        "topic": "Data Engineering & Streaming",
        "difficulty": "Medium",
        "method_name": "top_k_frequent",
        "description": (
            "### Top-K Frequent Stream Elements (Heavy Hitters)\n\n"
            "Given an incoming stream of tokens, return the $K$ most frequent elements.\n"
            "If frequencies tie, break ties alphabetically.\n\n"
            "#### Requirements\n"
            "Implement `top_k_frequent(stream, k)` returning list of top $k$ items sorted by descending frequency."
        ),
        "parameters": [
            {"name": "stream", "type": "List[str]", "description": "Stream of string tokens"},
            {"name": "k", "type": "int", "description": "Number of top elements to return"},
        ],
        "return_type": "List[str]",
        "constraints": [
            "1 <= k <= len(stream) <= 1000",
        ],
        "starter_code": (
            "from typing import List\n"
            "from collections import Counter\n\n"
            "class Solution:\n"
            "    def top_k_frequent(self, stream: List[str], k: int) -> List[str]:\n"
            "        # Write your top-k frequent stream implementation here\n"
            "        pass\n"
        ),
        "reference_solution": (
            "from typing import List\n"
            "from collections import Counter\n\n"
            "class Solution:\n"
            "    def top_k_frequent(self, stream: List[str], k: int) -> List[str]:\n"
            "        counts = Counter(stream)\n"
            "        # Sort by (-count, word)\n"
            "        sorted_items = sorted(counts.keys(), key=lambda w: (-counts[w], w))\n"
            "        return sorted_items[:k]\n"
        ),
        "test_cases": [
            {
                "input": [["apple", "banana", "apple", "cherry", "banana", "apple"], 2],
                "expected": ["apple", "banana"],
                "description": "apple (3), banana (2) are top 2",
            }
        ]
    })

    # 17. Principal Component Analysis (PCA) 1D Projection
    problems.append({
        "id": "step_18_pca_projection",
        "title": "Principal Component Analysis (PCA) Center & Covariance",
        "step": "Step 18 - AI/ML & Data Engineering",
        "topic": "Machine Learning Algorithms",
        "difficulty": "Hard",
        "method_name": "pca_center_and_covariance",
        "description": (
            "### Principal Component Analysis (PCA) Mean Centering & Covariance\n\n"
            "PCA seeks the orthogonal axes that maximize data variance.\n\n"
            "#### Equations\n"
            "1. **Mean Centering**: $X_c = X - \\mu$ where $\\mu_j = \\frac{1}{N}\\sum_{i=1}^N X_{ij}$\n"
            "2. **Sample Covariance Matrix**: $\\Sigma = \\frac{1}{N - 1} X_c^T X_c$\n\n"
            "#### Requirements\n"
            "Implement `pca_center_and_covariance(X)` returning `[centered_X, covariance_matrix]`."
        ),
        "parameters": [
            {"name": "X", "type": "List[List[float]]", "description": "N data samples of dimension D"},
        ],
        "return_type": "List[Any]",
        "constraints": [
            "2 <= N <= 100, 1 <= D <= 10",
            "Absolute tolerance 1e-4",
        ],
        "starter_code": (
            "from typing import List, Any\n\n"
            "class Solution:\n"
            "    def pca_center_and_covariance(self, X: List[List[float]]) -> List[Any]:\n"
            "        # Write your PCA centering and covariance here\n"
            "        pass\n"
        ),
        "reference_solution": (
            "from typing import List, Any\n\n"
            "class Solution:\n"
            "    def pca_center_and_covariance(self, X: List[List[float]]) -> List[Any]:\n"
            "        N = len(X)\n"
            "        D = len(X[0])\n\n"
            "        means = [sum(X[i][j] for i in range(N)) / N for j in range(D)]\n"
            "        X_c = [[round(X[i][j] - means[j], 4) for j in range(D)] for i in range(N)]\n\n"
            "        cov = []\n"
            "        for i in range(D):\n"
            "            row = []\n"
            "            for j in range(D):\n"
            "                val = sum(X_c[n][i] * X_c[n][j] for n in range(N)) / (N - 1)\n"
            "                row.append(round(val, 4))\n"
            "            cov.append(row)\n\n"
            "        return [X_c, cov]\n"
        ),
        "test_cases": [
            {
                "input": [[[1.0, 2.0], [3.0, 4.0], [5.0, 6.0]]],
                "expected": [
                    [[-2.0, -2.0], [0.0, 0.0], [2.0, 2.0]],
                    [[4.0, 4.0], [4.0, 4.0]]
                ],
                "description": "3 points centered around (3, 4) with sample covariance 4.0",
            }
        ]
    })

    # Save to JSON
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(problems, f, indent=2, ensure_ascii=False)

    print(f"Successfully generated {len(problems)} AI/ML & Data Engineering problems in {OUTPUT_FILE}")

if __name__ == "__main__":
    generate_curriculum()
