-- Evangelion colorschemes for Neovim.
--   :colorscheme evangelion            Unit-01
--   :colorscheme evangelion-unit-02    Unit-02
--   :colorscheme evangelion-rei        Rei (light)
--   :colorscheme evangelion-eoe        End of Evangelion

local M = {}

M.config = {
  transparent = false,
  italic_comments = true,
}

function M.setup(opts)
  M.config = vim.tbl_deep_extend("force", M.config, opts or {})
end

local function blend(fg, bg, alpha)
  local function rgb(c)
    c = c:gsub("#", "")
    return tonumber(c:sub(1, 2), 16), tonumber(c:sub(3, 4), 16), tonumber(c:sub(5, 6), 16)
  end
  local fr, fg_, fb = rgb(fg)
  local br, bg_, bb = rgb(bg)
  local function ch(a, b)
    return math.floor(a * alpha + b * (1 - alpha) + 0.5)
  end
  return string.format("#%02x%02x%02x", ch(fr, br), ch(fg_, bg_), ch(fb, bb))
end

local function highlights(p, cfg)
  local bg = cfg.transparent and "NONE" or p.background
  local italic = cfg.italic_comments

  return {
    -- Editor ---------------------------------------------------------------
    Normal = { fg = p.foreground, bg = bg },
    NormalNC = { fg = p.foreground, bg = bg },
    NormalFloat = { fg = p.foreground, bg = p.dark_background },
    FloatBorder = { fg = p.magenta, bg = p.dark_background },
    FloatTitle = { fg = p.orange, bg = p.dark_background, bold = true },
    Cursor = { fg = p.background, bg = p.bright_foreground },
    CursorLine = { bg = p.lighter_background },
    CursorColumn = { bg = p.lighter_background },
    ColorColumn = { bg = p.dark_background },
    CursorLineNr = { fg = p.orange, bold = true },
    LineNr = { fg = p.muted },
    SignColumn = { bg = bg },
    FoldColumn = { fg = p.muted, bg = bg },
    Folded = { fg = p.dark_foreground, bg = p.lighter_background, italic = true },
    VertSplit = { fg = p.selection },
    WinSeparator = { fg = p.selection },
    Visual = { bg = p.selection },
    VisualNOS = { bg = p.selection },
    Search = { fg = p.background, bg = p.yellow },
    IncSearch = { fg = p.background, bg = p.orange, bold = true },
    CurSearch = { fg = p.background, bg = p.orange, bold = true },
    Substitute = { fg = p.background, bg = p.red },
    MatchParen = { fg = p.orange, bold = true, underline = true },
    Pmenu = { fg = p.foreground, bg = p.dark_background },
    PmenuSel = { fg = p.bright_foreground, bg = p.selection, bold = true },
    PmenuSbar = { bg = p.dark_background },
    PmenuThumb = { bg = p.muted },
    StatusLine = { fg = p.foreground, bg = p.dark_background },
    StatusLineNC = { fg = p.dark_foreground, bg = p.dark_background },
    TabLine = { fg = p.dark_foreground, bg = p.dark_background },
    TabLineFill = { bg = p.darker_background },
    TabLineSel = { fg = p.bright_foreground, bg = p.selection, bold = true },
    WinBar = { fg = p.light_foreground, bold = true },
    WinBarNC = { fg = p.dark_foreground },
    Title = { fg = p.orange, bold = true },
    NonText = { fg = p.selection },
    Whitespace = { fg = p.selection },
    SpecialKey = { fg = p.muted },
    EndOfBuffer = { fg = bg == "NONE" and p.background or bg },
    Directory = { fg = p.blue, bold = true },
    Conceal = { fg = p.muted },
    ErrorMsg = { fg = p.red, bold = true },
    WarningMsg = { fg = p.orange, bold = true },
    ModeMsg = { fg = p.accent, bold = true },
    MoreMsg = { fg = p.accent },
    Question = { fg = p.cyan },
    QuickFixLine = { bg = p.selection, bold = true },
    WildMenu = { fg = p.background, bg = p.accent },
    SpellBad = { sp = p.red, undercurl = true },
    SpellCap = { sp = p.yellow, undercurl = true },
    SpellRare = { sp = p.magenta, undercurl = true },
    SpellLocal = { sp = p.cyan, undercurl = true },

    -- Syntax ---------------------------------------------------------------
    Comment = { fg = p.muted, italic = italic },
    Constant = { fg = p.orange },
    String = { fg = p.green },
    Character = { fg = p.green },
    Number = { fg = p.orange },
    Boolean = { fg = p.orange, bold = true },
    Float = { fg = p.orange },
    Identifier = { fg = p.foreground },
    Function = { fg = p.blue },
    Statement = { fg = p.magenta },
    Conditional = { fg = p.magenta },
    Repeat = { fg = p.magenta },
    Label = { fg = p.cyan },
    Operator = { fg = p.cyan },
    Keyword = { fg = p.magenta, italic = true },
    Exception = { fg = p.red },
    PreProc = { fg = p.yellow },
    Include = { fg = p.magenta },
    Define = { fg = p.magenta },
    Macro = { fg = p.yellow },
    PreCondit = { fg = p.yellow },
    Type = { fg = p.yellow },
    StorageClass = { fg = p.yellow },
    Structure = { fg = p.yellow },
    Typedef = { fg = p.yellow },
    Special = { fg = p.cyan },
    SpecialChar = { fg = p.red },
    Tag = { fg = p.red },
    Delimiter = { fg = p.light_foreground },
    SpecialComment = { fg = p.dark_foreground, italic = true },
    Debug = { fg = p.red },
    Underlined = { underline = true },
    Error = { fg = p.red, bold = true },
    Todo = { fg = p.background, bg = p.yellow, bold = true },

    -- Treesitter -----------------------------------------------------------
    ["@variable"] = { fg = p.foreground },
    ["@variable.builtin"] = { fg = p.red, italic = true },
    ["@variable.parameter"] = { fg = p.light_foreground, italic = true },
    ["@variable.member"] = { fg = p.cyan },
    ["@property"] = { fg = p.cyan },
    ["@constant"] = { fg = p.orange },
    ["@constant.builtin"] = { fg = p.orange, bold = true },
    ["@constant.macro"] = { fg = p.yellow },
    ["@module"] = { fg = p.yellow },
    ["@label"] = { fg = p.cyan },
    ["@string"] = { fg = p.green },
    ["@string.escape"] = { fg = p.red },
    ["@string.regexp"] = { fg = p.yellow },
    ["@string.special"] = { fg = p.cyan },
    ["@string.special.url"] = { fg = p.blue, underline = true },
    ["@character"] = { fg = p.green },
    ["@number"] = { fg = p.orange },
    ["@boolean"] = { fg = p.orange, bold = true },
    ["@type"] = { fg = p.yellow },
    ["@type.builtin"] = { fg = p.yellow, italic = true },
    ["@attribute"] = { fg = p.yellow },
    ["@function"] = { fg = p.blue },
    ["@function.builtin"] = { fg = p.blue, italic = true },
    ["@function.call"] = { fg = p.blue },
    ["@function.macro"] = { fg = p.yellow },
    ["@function.method"] = { fg = p.blue },
    ["@function.method.call"] = { fg = p.blue },
    ["@constructor"] = { fg = p.yellow },
    ["@operator"] = { fg = p.cyan },
    ["@keyword"] = { fg = p.magenta, italic = true },
    ["@keyword.function"] = { fg = p.magenta, italic = true },
    ["@keyword.return"] = { fg = p.red, italic = true },
    ["@keyword.operator"] = { fg = p.magenta },
    ["@keyword.import"] = { fg = p.magenta },
    ["@keyword.exception"] = { fg = p.red },
    ["@keyword.conditional"] = { fg = p.magenta },
    ["@keyword.repeat"] = { fg = p.magenta },
    ["@punctuation.delimiter"] = { fg = p.light_foreground },
    ["@punctuation.bracket"] = { fg = p.light_foreground },
    ["@punctuation.special"] = { fg = p.cyan },
    ["@comment"] = { link = "Comment" },
    ["@comment.todo"] = { link = "Todo" },
    ["@comment.error"] = { fg = p.background, bg = p.red, bold = true },
    ["@comment.warning"] = { fg = p.background, bg = p.orange, bold = true },
    ["@comment.note"] = { fg = p.background, bg = p.cyan, bold = true },
    ["@tag"] = { fg = p.red },
    ["@tag.attribute"] = { fg = p.yellow, italic = true },
    ["@tag.delimiter"] = { fg = p.muted },
    ["@markup.heading"] = { fg = p.orange, bold = true },
    ["@markup.heading.1"] = { fg = p.orange, bold = true },
    ["@markup.heading.2"] = { fg = p.accent, bold = true },
    ["@markup.heading.3"] = { fg = p.magenta, bold = true },
    ["@markup.heading.4"] = { fg = p.cyan, bold = true },
    ["@markup.strong"] = { bold = true },
    ["@markup.italic"] = { italic = true },
    ["@markup.strikethrough"] = { strikethrough = true },
    ["@markup.quote"] = { fg = p.dark_foreground, italic = true },
    ["@markup.link"] = { fg = p.blue },
    ["@markup.link.url"] = { fg = p.blue, underline = true },
    ["@markup.raw"] = { fg = p.green },
    ["@markup.list"] = { fg = p.orange },
    ["@diff.plus"] = { fg = p.green },
    ["@diff.minus"] = { fg = p.red },
    ["@diff.delta"] = { fg = p.yellow },

    -- LSP / diagnostics ----------------------------------------------------
    DiagnosticError = { fg = p.red },
    DiagnosticWarn = { fg = p.orange },
    DiagnosticInfo = { fg = p.cyan },
    DiagnosticHint = { fg = p.accent },
    DiagnosticOk = { fg = p.green },
    DiagnosticVirtualTextError = { fg = p.red, bg = blend(p.red, p.background, 0.1) },
    DiagnosticVirtualTextWarn = { fg = p.orange, bg = blend(p.orange, p.background, 0.1) },
    DiagnosticVirtualTextInfo = { fg = p.cyan, bg = blend(p.cyan, p.background, 0.1) },
    DiagnosticVirtualTextHint = { fg = p.accent, bg = blend(p.accent, p.background, 0.1) },
    DiagnosticUnderlineError = { sp = p.red, undercurl = true },
    DiagnosticUnderlineWarn = { sp = p.orange, undercurl = true },
    DiagnosticUnderlineInfo = { sp = p.cyan, undercurl = true },
    DiagnosticUnderlineHint = { sp = p.accent, undercurl = true },
    LspReferenceText = { bg = p.selection },
    LspReferenceRead = { bg = p.selection },
    LspReferenceWrite = { bg = p.selection, bold = true },
    LspInlayHint = { fg = p.dark_foreground, bg = blend(p.muted, p.background, 0.12), italic = true },
    LspSignatureActiveParameter = { fg = p.orange, bold = true },

    -- Diff / git -----------------------------------------------------------
    DiffAdd = { bg = blend(p.green, p.background, 0.15) },
    DiffChange = { bg = blend(p.yellow, p.background, 0.1) },
    DiffDelete = { bg = blend(p.red, p.background, 0.15) },
    DiffText = { bg = blend(p.yellow, p.background, 0.25) },
    Added = { fg = p.green },
    Changed = { fg = p.yellow },
    Removed = { fg = p.red },
    GitSignsAdd = { fg = p.green },
    GitSignsChange = { fg = p.yellow },
    GitSignsDelete = { fg = p.red },

    -- Plugins --------------------------------------------------------------
    TelescopeBorder = { fg = p.magenta, bg = p.dark_background },
    TelescopeNormal = { fg = p.foreground, bg = p.dark_background },
    TelescopePromptBorder = { fg = p.orange, bg = p.dark_background },
    TelescopePromptTitle = { fg = p.background, bg = p.orange, bold = true },
    TelescopeResultsTitle = { fg = p.background, bg = p.magenta, bold = true },
    TelescopePreviewTitle = { fg = p.background, bg = p.accent, bold = true },
    TelescopeSelection = { bg = p.selection, bold = true },
    TelescopeMatching = { fg = p.orange, bold = true },
    SnacksPickerBorder = { fg = p.magenta },
    SnacksPickerTitle = { fg = p.background, bg = p.orange, bold = true },
    SnacksPickerMatch = { fg = p.orange, bold = true },
    SnacksDashboardHeader = { fg = p.orange },
    SnacksDashboardKey = { fg = p.accent, bold = true },
    SnacksDashboardDesc = { fg = p.foreground },
    SnacksDashboardIcon = { fg = p.magenta },
    SnacksDashboardFooter = { fg = p.muted, italic = true },
    NeoTreeNormal = { fg = p.foreground, bg = p.dark_background },
    NeoTreeNormalNC = { fg = p.foreground, bg = p.dark_background },
    NeoTreeDirectoryName = { fg = p.blue },
    NeoTreeDirectoryIcon = { fg = p.magenta },
    NeoTreeRootName = { fg = p.orange, bold = true },
    NeoTreeGitModified = { fg = p.yellow },
    NeoTreeGitAdded = { fg = p.green },
    NeoTreeGitUntracked = { fg = p.cyan },
    WhichKey = { fg = p.accent },
    WhichKeyGroup = { fg = p.magenta },
    WhichKeyDesc = { fg = p.foreground },
    WhichKeySeparator = { fg = p.muted },
    BlinkCmpMenu = { fg = p.foreground, bg = p.dark_background },
    BlinkCmpMenuBorder = { fg = p.magenta, bg = p.dark_background },
    BlinkCmpMenuSelection = { bg = p.selection, bold = true },
    BlinkCmpLabelMatch = { fg = p.orange, bold = true },
    BlinkCmpKind = { fg = p.cyan },
    CmpItemAbbrMatch = { fg = p.orange, bold = true },
    CmpItemKind = { fg = p.cyan },
    IndentBlanklineChar = { fg = p.selection },
    IblIndent = { fg = p.selection },
    IblScope = { fg = p.magenta },
    SnacksIndent = { fg = p.selection },
    SnacksIndentScope = { fg = p.magenta },
    FlashLabel = { fg = p.background, bg = p.orange, bold = true },
    FlashMatch = { fg = p.cyan },
    FlashCurrent = { fg = p.accent, bold = true },
    NoiceCmdlinePopupBorder = { fg = p.magenta },
    NoiceCmdlineIcon = { fg = p.orange },
    NotifyERRORBorder = { fg = p.red },
    NotifyWARNBorder = { fg = p.orange },
    NotifyINFOBorder = { fg = p.accent },
    MiniStatuslineModeNormal = { fg = p.background, bg = p.accent, bold = true },
    MiniStatuslineModeInsert = { fg = p.background, bg = p.orange, bold = true },
    MiniStatuslineModeVisual = { fg = p.background, bg = p.magenta, bold = true },
    MiniStatuslineModeReplace = { fg = p.background, bg = p.red, bold = true },
    MiniStatuslineModeCommand = { fg = p.background, bg = p.yellow, bold = true },
  }
end

local function lualine_theme(p)
  local function mode(color)
    return {
      a = { fg = p.background, bg = color, gui = "bold" },
      b = { fg = p.foreground, bg = p.selection },
      c = { fg = p.light_foreground, bg = p.dark_background },
    }
  end
  return {
    normal = mode(p.accent),
    insert = mode(p.orange),
    visual = mode(p.magenta),
    replace = mode(p.red),
    command = mode(p.yellow),
    terminal = mode(p.cyan),
    inactive = mode(p.muted),
  }
end

function M.palette(name)
  return require("evangelion.palettes")[name or "evangelion"]
end

function M.load(name)
  local p = M.palette(name)
  if not p then
    vim.notify("evangelion: unknown variant " .. tostring(name), vim.log.levels.ERROR)
    return
  end

  if vim.g.colors_name then
    vim.cmd("hi clear")
  end
  vim.o.termguicolors = true
  vim.o.background = p.mode
  vim.g.colors_name = name

  for group, spec in pairs(highlights(p, M.config)) do
    vim.api.nvim_set_hl(0, group, spec)
  end

  local term = {
    p.dark_background, p.red, p.green, p.yellow, p.blue, p.magenta, p.cyan, p.foreground,
    p.muted, p.bright_red, p.bright_green, p.bright_yellow, p.bright_blue, p.bright_magenta, p.bright_cyan, p.bright_foreground,
  }
  for i, c in ipairs(term) do
    vim.g["terminal_color_" .. (i - 1)] = c
  end

  package.loaded["lualine.themes.evangelion"] = lualine_theme(p)
end

return M
