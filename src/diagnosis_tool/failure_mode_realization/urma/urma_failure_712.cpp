#include "urma_failure_712.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure712> g_urma("urma_712");

bool UrmaFailure712::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'convert_bond_port_id_to_active_index' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid port id, chip_id:' | grep -F ', port_idx:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure712::GetName() const
{
    return "激活端口所需输入对象无效导致激活端口失败";
}

std::string UrmaFailure712::GetRootCauseDesc() const
{
    return "函数用于激活端口，调用方传入的激活端口所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure712::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure712::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure712::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：convert_bond_port_id_to_active_index，Invalid port id, chip_id:，, port_idx:";
}

std::string UrmaFailure712::GetId() const
{
    return "urma_712";
}

} // namespace diag
