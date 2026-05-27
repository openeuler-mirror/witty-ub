#include "urma_failure_090.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure090> g_urma("urma_090");

bool UrmaFailure090::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_unimport_pjfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to alloc target jetty'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure090::GetName() const
{
    return "Jetty相关临时结构或命令参数分配失败";
}

std::string UrmaFailure090::GetRootCauseDesc() const
{
    return "函数在分配Jetty前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure090::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure090::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure090::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_unimport_pjfr，Failed to alloc target jetty";
}

std::string UrmaFailure090::GetId() const
{
    return "urma_090";
}

} // namespace diag
