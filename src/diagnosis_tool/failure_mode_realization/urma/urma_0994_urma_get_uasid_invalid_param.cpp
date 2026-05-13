#include "urma_0994_urma_get_uasid_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0994UrmaGetUasidInvalidParam> g_urma("urma_0994");

bool Urma0994UrmaGetUasidInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0994UrmaGetUasidInvalidParam::GetName() const
{
    return "urma_get_uasid 参数非法";
}

std::string Urma0994UrmaGetUasidInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `uasid == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0994UrmaGetUasidInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0994UrmaGetUasidInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0994UrmaGetUasidInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0994UrmaGetUasidInvalidParam::GetId() const
{
    return "urma_0994";
}
} // namespace diag
