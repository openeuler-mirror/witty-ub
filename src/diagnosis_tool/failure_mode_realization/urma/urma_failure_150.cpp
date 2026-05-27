#include "urma_failure_150.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure150> g_urma("urma_150");

bool UrmaFailure150::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_free_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'ioctl failed, ret:' | grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure150::GetName() const
{
    return "释放ioctl的ioctl调用返回失败";
}

std::string UrmaFailure150::GetRootCauseDesc() const
{
    return "函数通过ioctl向URMA内核驱动提交释放ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果"
           "。";
}

RootCause UrmaFailure150::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure150::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure150::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_free_jetty，ioctl failed, ret:，, errno:。";
}

std::string UrmaFailure150::GetId() const
{
    return "urma_150";
}

} // namespace diag
