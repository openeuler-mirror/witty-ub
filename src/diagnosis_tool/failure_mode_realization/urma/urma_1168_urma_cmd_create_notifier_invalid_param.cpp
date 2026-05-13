#include "urma_1168_urma_cmd_create_notifier_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1168UrmaCmdCreateNotifierInvalidParam> g_urma("urma_1168");

bool Urma1168UrmaCmdCreateNotifierInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1168UrmaCmdCreateNotifierInvalidParam::GetName() const
{
    return "urma_cmd_create_notifier 参数非法";
}

std::string Urma1168UrmaCmdCreateNotifierInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || ctx->dev_fd < 0`；该路径返回 -1";
}

RootCause Urma1168UrmaCmdCreateNotifierInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1168UrmaCmdCreateNotifierInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1168UrmaCmdCreateNotifierInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter";
}

std::string Urma1168UrmaCmdCreateNotifierInvalidParam::GetId() const
{
    return "urma_1168";
}
} // namespace diag
