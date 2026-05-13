#include "urma_0705_urma_delete_jetty_resource_delete_failure_1766.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0705UrmaDeleteJettyResourceDeleteFailure1766> g_urma("urma_0705");

bool Urma0705UrmaDeleteJettyResourceDeleteFailure1766::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {
        "[DRV_ERR]Failed to delete jetty, dev_name: %, eid_idx: %, id: %, ret: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0705UrmaDeleteJettyResourceDeleteFailure1766::GetName() const
{
    return "urma_delete_jetty 删除资源失败（日志行1766）";
}

std::string Urma0705UrmaDeleteJettyResourceDeleteFailure1766::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma0705UrmaDeleteJettyResourceDeleteFailure1766::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0705UrmaDeleteJettyResourceDeleteFailure1766::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0705UrmaDeleteJettyResourceDeleteFailure1766::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：[DRV_ERR]Failed to delete jetty, dev_name: %, eid_idx: %, id: %, "
           "ret: %.";
}

std::string Urma0705UrmaDeleteJettyResourceDeleteFailure1766::GetId() const
{
    return "urma_0705";
}
} // namespace diag
