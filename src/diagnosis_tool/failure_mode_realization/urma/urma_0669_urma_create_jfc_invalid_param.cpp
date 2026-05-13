#include "urma_0669_urma_create_jfc_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0669UrmaCreateJfcInvalidParam> g_urma("urma_0669");

bool Urma0669UrmaCreateJfcInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0669UrmaCreateJfcInvalidParam::GetName() const
{
    return "urma_create_jfc 参数非法";
}

std::string Urma0669UrmaCreateJfcInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `ctx == NULL || jfc_cfg == NULL`；该路径返回 NULL";
}

RootCause Urma0669UrmaCreateJfcInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0669UrmaCreateJfcInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0669UrmaCreateJfcInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0669UrmaCreateJfcInvalidParam::GetId() const
{
    return "urma_0669";
}
} // namespace diag
