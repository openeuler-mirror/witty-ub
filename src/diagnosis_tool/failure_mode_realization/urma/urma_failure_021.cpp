#include "urma_failure_021.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure021> g_urma("urma_021");

bool UrmaFailure021::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_provider_bond_uninit' \"$URMA_LOG_PATH\" 2>/dev/null | grep -F "
        "'Provider Bond register ops not registered.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure021::GetName() const
{
    return "URMA资源注册时下层资源准备失败";
}

std::string UrmaFailure021::GetRootCauseDesc() const
{
    return "函数负责注册URMA资源，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
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
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_provider_bond_uninit，Provider Bond register ops not registered.。";
}

std::string UrmaFailure021::GetId() const
{
    return "urma_021";
}

} // namespace diag
