#include "urma_0523_urma_cmd_modify_tp_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0523UrmaCmdModifyTpInvalidParam> g_urma("urma_0523");

bool Urma0523UrmaCmdModifyTpInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0523UrmaCmdModifyTpInvalidParam::GetName() const
{
    return "urma_cmd_modify_tp 参数非法";
}

std::string Urma0523UrmaCmdModifyTpInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev_fd < 0 || cfg == NULL || attr == NULL`；该路径返回 "
           "-1";
}

RootCause Urma0523UrmaCmdModifyTpInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0523UrmaCmdModifyTpInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0523UrmaCmdModifyTpInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0523UrmaCmdModifyTpInvalidParam::GetId() const
{
    return "urma_0523";
}
} // namespace diag
