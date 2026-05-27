#include "urma_failure_340.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure340> g_urma("urma_340");

bool UrmaFailure340::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'get_topo_info_from_ko' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to create topo map'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure340::GetName() const
{
    return "context创建时下层资源准备失败";
}

std::string UrmaFailure340::GetRootCauseDesc() const
{
    return "函数负责创建context，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure340::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure340::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure340::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：get_topo_info_from_ko，Failed to create topo map";
}

std::string UrmaFailure340::GetId() const
{
    return "urma_340";
}

} // namespace diag
