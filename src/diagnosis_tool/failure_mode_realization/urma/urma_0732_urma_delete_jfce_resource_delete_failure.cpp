#include "urma_0732_urma_delete_jfce_resource_delete_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0732UrmaDeleteJfceResourceDeleteFailure> g_urma("urma_0732");

bool Urma0732UrmaDeleteJfceResourceDeleteFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"[DRV_ERR]Failed to delete jfce, ret: %"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0732UrmaDeleteJfceResourceDeleteFailure::GetName() const
{
    return "urma_delete_jfce 删除资源失败";
}

std::string Urma0732UrmaDeleteJfceResourceDeleteFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 ret";
}

RootCause Urma0732UrmaDeleteJfceResourceDeleteFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0732UrmaDeleteJfceResourceDeleteFailure::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string Urma0732UrmaDeleteJfceResourceDeleteFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：[DRV_ERR]Failed to delete jfce, ret: %";
}

std::string Urma0732UrmaDeleteJfceResourceDeleteFailure::GetId() const
{
    return "urma_0732";
}
} // namespace diag
