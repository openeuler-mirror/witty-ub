#include "urma_failure_591.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure591> g_urma("urma_591");

bool UrmaFailure591::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && "
        "grep -F 'urma_import_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Token value must be set when token policy is not URMA_TOKEN_NONE'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure591::GetName() const
{
    return "urma_import_jfr 读取或解析 sysfs 设备/EID/端口信息失败导致设备信息不可用";
}

std::string UrmaFailure591::GetRootCauseDesc() const
{
    return "urma_import_jfr 依赖 sysfs 中的设备、EID、端口、能力或 cdev 路径信息枚举 URMA "
           "设备并构建设备属性，但文件打开、读取、格式化路径或内容解析失败，导致设备、端口或 EID "
           "信息无法被用户态正确使用。";
}

RootCause UrmaFailure591::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure591::GetFixSuggDesc() const
{
    return "UDMA 错误定界；建链交换信息失败，可重试";
}

std::string UrmaFailure591::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 中匹配关键日志：Token value must be set when token policy is not URMA_TOKEN_NONE";
}

std::string UrmaFailure591::GetId() const
{
    return "urma_591";
}

} // namespace diag
