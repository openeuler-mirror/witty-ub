#include "urma_1026_urma_cmd_register_seg_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1026UrmaCmdRegisterSegInvalidParam> g_urma("urma_1026");

bool Urma1026UrmaCmdRegisterSegInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1026UrmaCmdRegisterSegInvalidParam::GetName() const
{
    return "urma_cmd_register_seg 参数非法";
}

std::string Urma1026UrmaCmdRegisterSegInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev_fd < 0 || tseg == NULL || cfg == NULL || cfg->va == "
           "0`；该路径返回 -1";
}

RootCause Urma1026UrmaCmdRegisterSegInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1026UrmaCmdRegisterSegInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1026UrmaCmdRegisterSegInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma1026UrmaCmdRegisterSegInvalidParam::GetId() const
{
    return "urma_1026";
}
} // namespace diag
