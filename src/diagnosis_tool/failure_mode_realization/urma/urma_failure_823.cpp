#include "urma_failure_823.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure823> g_urma("urma_823");

bool UrmaFailure823::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        R"(test -n "$URMA_LOG_PATH" && grep -F 'urma_discover_devices' "$URMA_LOG_PATH" 2>/dev/null | grep -F 'open failed, errno:')");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure823::GetName() const
{
    return "urma_discover_devices 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用";
}

std::string UrmaFailure823::GetRootCauseDesc() const
{
    return "urma_discover_devices 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA "
           "设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID "
           "信息无法被用户态正确使用。";
}

RootCause UrmaFailure823::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure823::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure823::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：open failed, errno";
}

std::string UrmaFailure823::GetId() const
{
    return "urma_823";
}

} // namespace diag
