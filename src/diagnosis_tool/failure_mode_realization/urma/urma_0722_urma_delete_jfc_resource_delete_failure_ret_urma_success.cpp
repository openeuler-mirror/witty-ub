#include "urma_0722_urma_delete_jfc_resource_delete_failure_ret_urma_success.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0722UrmaDeleteJfcResourceDeleteFailureRetUrmaSuccess> g_urma("urma_0722");

bool Urma0722UrmaDeleteJfcResourceDeleteFailureRetUrmaSuccess::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {
        "[DRV_ERR]Failed to delete jfc, dev_name: %, eid_idx: %, id: %, ret: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0722UrmaDeleteJfcResourceDeleteFailureRetUrmaSuccess::GetName() const
{
    return "urma_delete_jfc 删除资源失败（ret != URMA_SUCCESS）";
}

std::string Urma0722UrmaDeleteJfcResourceDeleteFailureRetUrmaSuccess::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求";
}

RootCause Urma0722UrmaDeleteJfcResourceDeleteFailureRetUrmaSuccess::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0722UrmaDeleteJfcResourceDeleteFailureRetUrmaSuccess::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0722UrmaDeleteJfcResourceDeleteFailureRetUrmaSuccess::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：[DRV_ERR]Failed to delete jfc, dev_name: %, eid_idx: %, id: %, "
           "ret: %.";
}

std::string Urma0722UrmaDeleteJfcResourceDeleteFailureRetUrmaSuccess::GetId() const
{
    return "urma_0722";
}
} // namespace diag
