#include "urma_failure_436.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure436> g_urma("urma_436");

bool UrmaFailure436::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_get_jfr_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'ioctl failed in urma_cmd_get_jfr_opt, ret:' | grep -F ', errno:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure436::GetName() const
{
    return "获取ioctl的ioctl调用返回失败";
}

std::string UrmaFailure436::GetRootCauseDesc() const
{
    return "函数通过ioctl向URMA内核驱动提交获取ioctl请求，驱动返回错误或系统调用失败，用户态无法获得预期的驱动处理结果"
           "。";
}

RootCause UrmaFailure436::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure436::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure436::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_get_jfr_opt，ioctl failed in urma_cmd_get_jfr_opt, ret:，, errno:";
}

std::string UrmaFailure436::GetId() const
{
    return "urma_436";
}

} // namespace diag
