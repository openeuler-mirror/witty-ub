#include "urma_failure_412.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure412> g_urma("urma_412");

bool UrmaFailure412::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_register_sysfs_dev' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'Register device failed. Failed to match driver for device'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure412::GetName() const
{
    return "设备注册时下层资源准备失败";
}

std::string UrmaFailure412::GetRootCauseDesc() const
{
    return "函数负责注册设备，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure412::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure412::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure412::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_register_sysfs_dev，Register device failed. Failed to match driver "
           "for device。";
}

std::string UrmaFailure412::GetId() const
{
    return "urma_412";
}

} // namespace diag
