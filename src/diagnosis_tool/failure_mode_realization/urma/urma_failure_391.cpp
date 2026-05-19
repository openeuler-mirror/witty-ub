#include "urma_failure_391.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure391> g_urma("urma_391");

bool UrmaFailure391::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_alloc_jfs' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'jfs cfg out of range, depth:' | grep -F ', max_depth:' | grep -F ', inline_data:' | grep -F ', max_inline_len:' | grep -F ', sge:' | grep -F ', max_sge:' | grep -F ', rsge:' | grep -F ', max_rsge:')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure391::GetName() const
{
    return "urma_alloc_jfs 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用";
}

std::string UrmaFailure391::GetRootCauseDesc() const
{
    return "urma_alloc_jfs 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA "
           "设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID "
           "信息无法被用户态正确使用。";
}

RootCause UrmaFailure391::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure391::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure391::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：jfs cfg out of range, depth:, max_depth:, inline_data:, max_inline_len:, "
           "sge:, max_sge:, rsge:, max_rsge";
}

std::string UrmaFailure391::GetId() const
{
    return "urma_391";
}

} // namespace diag
