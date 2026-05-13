#include "urma_1149_urma_free_net_addr_list_invalid_param.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma1149UrmaFreeNetAddrListInvalidParam> g_urma("urma_1149");

bool Urma1149UrmaFreeNetAddrListInvalidParam::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma1149UrmaFreeNetAddrListInvalidParam::GetName() const
{
    return "urma_free_net_addr_list 参数非法";
}

std::string Urma1149UrmaFreeNetAddrListInvalidParam::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `net_addr_list == NULL`";
}

RootCause Urma1149UrmaFreeNetAddrListInvalidParam::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma1149UrmaFreeNetAddrListInvalidParam::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma1149UrmaFreeNetAddrListInvalidParam::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma1149UrmaFreeNetAddrListInvalidParam::GetId() const
{
    return "urma_1149";
}
} // namespace diag
