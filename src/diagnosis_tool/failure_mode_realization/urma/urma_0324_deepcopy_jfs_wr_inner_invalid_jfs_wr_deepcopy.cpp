#include "urma_0324_deepcopy_jfs_wr_inner_invalid_jfs_wr_deepcopy.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0324DeepcopyJfsWrInnerInvalidJfsWrDeepcopy> g_urma("urma_0324");

bool Urma0324DeepcopyJfsWrInnerInvalidJfsWrDeepcopy::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid jfs wr to deepcopy"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0324DeepcopyJfsWrInnerInvalidJfsWrDeepcopy::GetName() const
{
    return "deepcopy_jfs_wr_inner Invalid jfs wr to deepcopy";
}

std::string Urma0324DeepcopyJfsWrInnerInvalidJfsWrDeepcopy::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `wr == NULL`；该路径返回 NULL";
}

RootCause Urma0324DeepcopyJfsWrInnerInvalidJfsWrDeepcopy::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0324DeepcopyJfsWrInnerInvalidJfsWrDeepcopy::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0324DeepcopyJfsWrInnerInvalidJfsWrDeepcopy::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid jfs wr to deepcopy";
}

std::string Urma0324DeepcopyJfsWrInnerInvalidJfsWrDeepcopy::GetId() const
{
    return "urma_0324";
}
} // namespace diag
