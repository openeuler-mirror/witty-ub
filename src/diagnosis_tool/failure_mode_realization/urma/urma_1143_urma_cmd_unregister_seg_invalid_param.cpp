#include "urma_1143_urma_cmd_unregister_seg_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1143UrmaCmdUnregisterSegInvalidParam> g_urma("urma_1143");

bool Urma1143UrmaCmdUnregisterSegInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1143UrmaCmdUnregisterSegInvalidParam::GetName() const
{
    return "urma_cmd_unregister_seg 参数非法";
}

std::string Urma1143UrmaCmdUnregisterSegInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `tseg == NULL || tseg->urma_ctx == NULL || tseg->urma_ctx->dev_fd < "
           "0`；该路径返回 -1";
}

RootCause Urma1143UrmaCmdUnregisterSegInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1143UrmaCmdUnregisterSegInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1143UrmaCmdUnregisterSegInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma1143UrmaCmdUnregisterSegInvalidParam::GetId() const
{
    return "urma_1143";
}
} // namespace diag
