#include "urma_0648_urma_create_jetty_drv_err_create_jetty_failed_dev_na.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0648UrmaCreateJettyDrvErrCreateJettyFailedDevNa> g_urma("urma_0648");

bool Urma0648UrmaCreateJettyDrvErrCreateJettyFailedDevNa::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"[DRV_ERR]create_jetty failed, dev_name: %, eid_idx: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0648UrmaCreateJettyDrvErrCreateJettyFailedDevNa::GetName() const
{
    return "urma_create_jetty [DRV_ERR]create_jetty failed, dev_na";
}

std::string Urma0648UrmaCreateJettyDrvErrCreateJettyFailedDevNa::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 NULL";
}

RootCause Urma0648UrmaCreateJettyDrvErrCreateJettyFailedDevNa::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0648UrmaCreateJettyDrvErrCreateJettyFailedDevNa::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0648UrmaCreateJettyDrvErrCreateJettyFailedDevNa::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：[DRV_ERR]create_jetty failed, dev_name: %, eid_idx: %.";
}

std::string Urma0648UrmaCreateJettyDrvErrCreateJettyFailedDevNa::GetId() const
{
    return "urma_0648";
}
} // namespace diag
