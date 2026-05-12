#include "urma_0718_urma_delete_jetty_grp_resource_delete_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0718UrmaDeleteJettyGrpResourceDeleteFailure> g_urma("urma_0718");

bool Urma0718UrmaDeleteJettyGrpResourceDeleteFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"failed to delete jetty to jetty_grp."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0718UrmaDeleteJettyGrpResourceDeleteFailure::GetName() const
{
    return "urma_delete_jetty_to_jetty_grp 删除资源失败";
}

std::string Urma0718UrmaDeleteJettyGrpResourceDeleteFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "-1";
}

RootCause Urma0718UrmaDeleteJettyGrpResourceDeleteFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0718UrmaDeleteJettyGrpResourceDeleteFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0718UrmaDeleteJettyGrpResourceDeleteFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：failed to delete jetty to jetty_grp.";
}

std::string Urma0718UrmaDeleteJettyGrpResourceDeleteFailure::GetId() const
{
    return "urma_0718";
}
} // namespace diag
