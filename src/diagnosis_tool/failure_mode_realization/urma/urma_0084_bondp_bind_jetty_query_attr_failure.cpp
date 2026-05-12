#include "urma_0084_bondp_bind_jetty_query_attr_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0084BondpBindJettyQueryAttrFailure> g_urma("urma_0084");

bool Urma0084BondpBindJettyQueryAttrFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Jetty already has a binded target jetty"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0084BondpBindJettyQueryAttrFailure::GetName() const
{
    return "bondp_bind_jetty 查询属性失败";
}

std::string Urma0084BondpBindJettyQueryAttrFailure::GetRootCauseDesc() const
{
    return "读取 sysfs 或设备文件失败，可能由于设备未注册、路径不存在、权限不足或读取返回异常；该路径返回 URMA_EINVAL";
}

RootCause Urma0084BondpBindJettyQueryAttrFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0084BondpBindJettyQueryAttrFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0084BondpBindJettyQueryAttrFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Jetty already has a binded target jetty";
}

std::string Urma0084BondpBindJettyQueryAttrFailure::GetId() const
{
    return "urma_0084";
}
} // namespace diag
