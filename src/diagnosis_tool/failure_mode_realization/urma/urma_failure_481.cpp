#include "urma_failure_481.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure481> g_urma("urma_481");

bool UrmaFailure481::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_query_device_attr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to open urma cdev, path'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure481::GetName() const
{
    return "字符设备路径信息的sysfs读取或解析失败";
}

std::string UrmaFailure481::GetRootCauseDesc() const
{
    return "函数需要从sysfs获取字符设备路径信息来构建设备上下文，文件打开、读取或内容解析失败导致URMA无法完成设备发现或"
           "能力初始化。";
}

RootCause UrmaFailure481::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure481::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure481::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_query_device_attr，Failed to open urma cdev, path";
}

std::string UrmaFailure481::GetId() const
{
    return "urma_481";
}

} // namespace diag
