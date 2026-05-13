#include "urma_0710_urma_delete_jetty_batch_resource_delete_failure_jetty_cfg_jfs.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0710UrmaDeleteJettyBatchResourceDeleteFailureJettyCfgJfs> g_urma("urma_0710");

bool Urma0710UrmaDeleteJettyBatchResourceDeleteFailureJettyCfgJfs::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to delete as jetty has remote jetty, try unbind, index: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0710UrmaDeleteJettyBatchResourceDeleteFailureJettyCfgJfs::GetName() const
{
    return "urma_delete_jetty_batch 删除资源失败（jetty->jetty_cfg.jfs_cfg.trans_mode == URMA_TM_RC && "
           "jetty->remote_jetty != NULL）";
}

std::string Urma0710UrmaDeleteJettyBatchResourceDeleteFailureJettyCfgJfs::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误";
}

RootCause Urma0710UrmaDeleteJettyBatchResourceDeleteFailureJettyCfgJfs::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0710UrmaDeleteJettyBatchResourceDeleteFailureJettyCfgJfs::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0710UrmaDeleteJettyBatchResourceDeleteFailureJettyCfgJfs::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to delete as jetty has remote jetty, try unbind, index: %";
}

std::string Urma0710UrmaDeleteJettyBatchResourceDeleteFailureJettyCfgJfs::GetId() const
{
    return "urma_0710";
}
} // namespace diag
