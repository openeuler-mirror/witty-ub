#include "urma_0003_bondp_jfce_init_comp_attr_not_single_die_fail_create.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0003BondpJfceInitCompAttrNotSingleDieFailCreate> g_urma("urma_0003");

bool Urma0003BondpJfceInitCompAttrNotSingleDieFailCreate::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Fail to create epoll_fd."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0003BondpJfceInitCompAttrNotSingleDieFailCreate::GetName() const
{
    return "bondp_jfce_init_comp_attr_not_single_die Fail to create epoll_fd.";
}

std::string Urma0003BondpJfceInitCompAttrNotSingleDieFailCreate::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_FAIL";
}

RootCause Urma0003BondpJfceInitCompAttrNotSingleDieFailCreate::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0003BondpJfceInitCompAttrNotSingleDieFailCreate::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0003BondpJfceInitCompAttrNotSingleDieFailCreate::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Fail to create epoll_fd.";
}

std::string Urma0003BondpJfceInitCompAttrNotSingleDieFailCreate::GetId() const
{
    return "urma_0003";
}
} // namespace diag
