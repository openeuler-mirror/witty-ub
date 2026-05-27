#include "urma_failure_377.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure377> g_urma("urma_377");

bool UrmaFailure377::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_create_jfce' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'ioctl failed in urma_cmd_create_jfce, ret:' | grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure377::GetName() const
{
    return "创建ioctl的ioctl调用返回失败";
}

std::string UrmaFailure377::GetRootCauseDesc() const
{
    return "函数通过ioctl向URMA内核驱动提交创建ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果"
           "。";
}

RootCause UrmaFailure377::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure377::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure377::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_create_jfce，ioctl failed in urma_cmd_create_jfce, ret:，, errno:";
}

std::string UrmaFailure377::GetId() const
{
    return "urma_377";
}

} // namespace diag
