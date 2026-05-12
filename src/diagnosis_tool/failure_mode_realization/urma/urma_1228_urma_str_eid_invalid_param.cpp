#include "urma_1228_urma_str_eid_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1228UrmaStrEidInvalidParam> g_urma("urma_1228");

bool Urma1228UrmaStrEidInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid argument."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1228UrmaStrEidInvalidParam::GetName() const
{
    return "urma_str_to_eid 参数非法";
}

std::string Urma1228UrmaStrEidInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `buf == NULL || strlen(buf) < URMA_EID_STR_MIN_LEN || eid == "
           "NULL`；该路径返回 -EINVAL";
}

RootCause Urma1228UrmaStrEidInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1228UrmaStrEidInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1228UrmaStrEidInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid argument.";
}

std::string Urma1228UrmaStrEidInvalidParam::GetId() const
{
    return "urma_1228";
}
} // namespace diag
