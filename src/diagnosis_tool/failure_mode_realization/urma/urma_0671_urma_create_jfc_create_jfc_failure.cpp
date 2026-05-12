#include "urma_0671_urma_create_jfc_create_jfc_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0671UrmaCreateJfcCreateJfcFailure> g_urma("urma_0671");

bool Urma0671UrmaCreateJfcCreateJfcFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"[DRV_ERR]Failed to create jfc, dev_name: %, eid_idx: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0671UrmaCreateJfcCreateJfcFailure::GetName() const
{
    return "urma_create_jfc 创建JFC失败";
}

std::string Urma0671UrmaCreateJfcCreateJfcFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 jfc";
}

RootCause Urma0671UrmaCreateJfcCreateJfcFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0671UrmaCreateJfcCreateJfcFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0671UrmaCreateJfcCreateJfcFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：[DRV_ERR]Failed to create jfc, dev_name: %, eid_idx: %.";
}

std::string Urma0671UrmaCreateJfcCreateJfcFailure::GetId() const
{
    return "urma_0671";
}
} // namespace diag
