#include "urma_failure_367.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure367> g_urma("urma_367");

bool UrmaFailure367::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_create_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'ioctl failed in urma_cmd_create_jfr, ret:' | grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure367::GetName() const
{
    return "创建ioctl的ioctl调用返回失败";
}

std::string UrmaFailure367::GetRootCauseDesc() const
{
    return "函数通过ioctl向URMA内核驱动提交创建ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果"
           "。";
}

RootCause UrmaFailure367::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure367::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure367::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_create_jfr，ioctl failed in urma_cmd_create_jfr, ret:，, errno:";
}

std::string UrmaFailure367::GetId() const
{
    return "urma_367";
}

} // namespace diag
