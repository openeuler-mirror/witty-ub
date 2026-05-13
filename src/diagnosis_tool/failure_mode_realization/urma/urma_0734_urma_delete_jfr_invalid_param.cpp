#include "urma_0734_urma_delete_jfr_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0734UrmaDeleteJfrInvalidParam> g_urma("urma_0734");

bool Urma0734UrmaDeleteJfrInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0734UrmaDeleteJfrInvalidParam::GetName() const
{
    return "urma_delete_jfr 参数非法";
}

std::string Urma0734UrmaDeleteJfrInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfr == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0734UrmaDeleteJfrInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0734UrmaDeleteJfrInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0734UrmaDeleteJfrInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0734UrmaDeleteJfrInvalidParam::GetId() const
{
    return "urma_0734";
}
} // namespace diag
