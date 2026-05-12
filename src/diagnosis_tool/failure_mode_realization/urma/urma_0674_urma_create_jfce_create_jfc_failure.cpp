#include "urma_0674_urma_create_jfce_create_jfc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0674UrmaCreateJfceCreateJfcFailure> g_urma("urma_0674");

bool Urma0674UrmaCreateJfceCreateJfcFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"[DRV_ERR]Failed to create jfce, dev_name: %, eid_idx: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0674UrmaCreateJfceCreateJfcFailure::GetName() const
{
    return "urma_create_jfce 创建JFC失败";
}

std::string Urma0674UrmaCreateJfceCreateJfcFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 NULL";
}

RootCause Urma0674UrmaCreateJfceCreateJfcFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0674UrmaCreateJfceCreateJfcFailure::GetFixSuggDesc() const
{
    return "当前预期不会出现，如果fd超规格可能导致失败，此时需要修改系统fd规格数，或者减小应用创建jfce的数量";
}

std::string Urma0674UrmaCreateJfceCreateJfcFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：[DRV_ERR]Failed to create jfce, dev_name: %, eid_idx: %.";
}

std::string Urma0674UrmaCreateJfceCreateJfcFailure::GetId() const
{
    return "urma_0674";
}
} // namespace diag
