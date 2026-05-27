#include "urma_failure_021.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure021> g_urma("urma_021");

bool UrmaFailure021::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_global_ctx_init' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to alloc global context'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure021::GetName() const
{
    return "context相关临时结构或命令参数分配失败";
}

std::string UrmaFailure021::GetRootCauseDesc() const
{
    return "函数在分配context前需要申请命令参数、资源描述或临时缓存，内存分配失败会阻断后续URMA资源处理。";
}

RootCause UrmaFailure021::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure021::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure021::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_global_ctx_init，Failed to alloc global context";
}

std::string UrmaFailure021::GetId() const
{
    return "urma_021";
}

} // namespace diag
