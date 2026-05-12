#include "urma_0318_deepcopy_jfr_wr_inner_invalid_jfr_wr_deepcopy.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0318DeepcopyJfrWrInnerInvalidJfrWrDeepcopy> g_urma("urma_0318");

bool Urma0318DeepcopyJfrWrInnerInvalidJfrWrDeepcopy::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid jfr wr to deepcopy"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0318DeepcopyJfrWrInnerInvalidJfrWrDeepcopy::GetName() const
{
    return "deepcopy_jfr_wr_inner Invalid jfr wr to deepcopy";
}

std::string Urma0318DeepcopyJfrWrInnerInvalidJfrWrDeepcopy::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `wr == NULL`；该路径返回 NULL";
}

RootCause Urma0318DeepcopyJfrWrInnerInvalidJfrWrDeepcopy::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0318DeepcopyJfrWrInnerInvalidJfrWrDeepcopy::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0318DeepcopyJfrWrInnerInvalidJfrWrDeepcopy::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid jfr wr to deepcopy";
}

std::string Urma0318DeepcopyJfrWrInnerInvalidJfrWrDeepcopy::GetId() const
{
    return "urma_0318";
}
} // namespace diag
