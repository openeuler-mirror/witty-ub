#include "urma_0736_urma_delete_jfr_resource_delete_failure_status_urma_success.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0736UrmaDeleteJfrResourceDeleteFailureStatusUrmaSuccess> g_urma("urma_0736");

bool Urma0736UrmaDeleteJfrResourceDeleteFailureStatusUrmaSuccess::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {
        "[DRV_ERR]Failed to delete jfr, dev_name: %, eid_idx: %, id: %, status: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0736UrmaDeleteJfrResourceDeleteFailureStatusUrmaSuccess::GetName() const
{
    return "urma_delete_jfr 删除资源失败（status != URMA_SUCCESS）";
}

std::string Urma0736UrmaDeleteJfrResourceDeleteFailureStatusUrmaSuccess::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 status";
}

RootCause Urma0736UrmaDeleteJfrResourceDeleteFailureStatusUrmaSuccess::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0736UrmaDeleteJfrResourceDeleteFailureStatusUrmaSuccess::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0736UrmaDeleteJfrResourceDeleteFailureStatusUrmaSuccess::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：[DRV_ERR]Failed to delete jfr, dev_name: %, eid_idx: %, id: %, "
           "status: %.";
}

std::string Urma0736UrmaDeleteJfrResourceDeleteFailureStatusUrmaSuccess::GetId() const
{
    return "urma_0736";
}
} // namespace diag
