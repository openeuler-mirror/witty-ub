#include "urma_0382_urma_cmd_create_jetty_create_jetty_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0382UrmaCmdCreateJettyCreateJettyFailure> g_urma("urma_0382");

bool Urma0382UrmaCmdCreateJettyCreateJettyFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"failed to init create jetty cmd"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0382UrmaCmdCreateJettyCreateJettyFailure::GetName() const
{
    return "urma_cmd_create_jetty 创建Jetty失败";
}

std::string Urma0382UrmaCmdCreateJettyCreateJettyFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "-1";
}

RootCause Urma0382UrmaCmdCreateJettyCreateJettyFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0382UrmaCmdCreateJettyCreateJettyFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0382UrmaCmdCreateJettyCreateJettyFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：failed to init create jetty cmd";
}

std::string Urma0382UrmaCmdCreateJettyCreateJettyFailure::GetId() const
{
    return "urma_0382";
}
} // namespace diag
