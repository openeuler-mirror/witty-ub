#include "urma_0684_urma_create_jfs_create_jfs_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0684UrmaCreateJfsCreateJfsFailure> g_urma("urma_0684");

bool Urma0684UrmaCreateJfsCreateJfsFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"[DRV_ERR]Failed to create jfs, dev_name: %, eid_idx: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0684UrmaCreateJfsCreateJfsFailure::GetName() const
{
    return "urma_create_jfs 创建JFS失败";
}

std::string Urma0684UrmaCreateJfsCreateJfsFailure::GetRootCauseDesc() const
{
    return "用户态向内核/驱动下发命令失败，通常表示驱动返回错误、设备状态异常或权限/参数不满足要求；该路径返回 jfs";
}

RootCause Urma0684UrmaCreateJfsCreateJfsFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0684UrmaCreateJfsCreateJfsFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0684UrmaCreateJfsCreateJfsFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：[DRV_ERR]Failed to create jfs, dev_name: %, eid_idx: %.";
}

std::string Urma0684UrmaCreateJfsCreateJfsFailure::GetId() const
{
    return "urma_0684";
}
} // namespace diag
