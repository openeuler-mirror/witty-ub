#include "urma_0746_urma_delete_jfs_resource_delete_failure_ret_urma_success.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0746UrmaDeleteJfsResourceDeleteFailureRetUrmaSuccess> g_urma("urma_0746");

bool Urma0746UrmaDeleteJfsResourceDeleteFailureRetUrmaSuccess::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {
        "[DRV_ERR]Failed to delete jfs, dev_name: %, eid_idx: %, id: %, ret: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0746UrmaDeleteJfsResourceDeleteFailureRetUrmaSuccess::GetName() const
{
    return "urma_delete_jfs 删除资源失败（ret != URMA_SUCCESS）";
}

std::string Urma0746UrmaDeleteJfsResourceDeleteFailureRetUrmaSuccess::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma0746UrmaDeleteJfsResourceDeleteFailureRetUrmaSuccess::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0746UrmaDeleteJfsResourceDeleteFailureRetUrmaSuccess::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0746UrmaDeleteJfsResourceDeleteFailureRetUrmaSuccess::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：[DRV_ERR]Failed to delete jfs, dev_name: %, eid_idx: %, id: %, "
           "ret: %.";
}

std::string Urma0746UrmaDeleteJfsResourceDeleteFailureRetUrmaSuccess::GetId() const
{
    return "urma_0746";
}
} // namespace diag
