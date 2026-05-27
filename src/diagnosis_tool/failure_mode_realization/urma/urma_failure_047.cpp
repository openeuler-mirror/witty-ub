#include "urma_failure_047.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure047> g_urma("urma_047");

bool UrmaFailure047::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_init' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'None of the providers registered.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure047::GetName() const
{
    return "URMA资源初始化时下层资源准备失败";
}

std::string UrmaFailure047::GetRootCauseDesc() const
{
    return "函数负责初始化URMA资源，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure047::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure047::GetFixSuggDesc() const
{
    return "查看/usr/lib64/urma目录下，是否存在liburma_udma.so等驱动文件，或查看文件是否具备x权限，完成正确部署后重试";
}

std::string UrmaFailure047::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_init，None of the providers registered.";
}

std::string UrmaFailure047::GetId() const
{
    return "urma_047";
}

} // namespace diag
