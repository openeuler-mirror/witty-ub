#include "urma_1071_schedule_next_recv_port_matrix_singlepath_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma1071ScheduleNextRecvPortMatrixSinglepathFunctionFailure> g_urma("urma_1071");

bool Urma1071ScheduleNextRecvPortMatrixSinglepathFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_1072"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma1071ScheduleNextRecvPortMatrixSinglepathFunctionFailure::GetName() const
{
    return "schedule_next_recv_port_matrix_singlepath 函数故障";
}

std::string Urma1071ScheduleNextRecvPortMatrixSinglepathFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma1071ScheduleNextRecvPortMatrixSinglepathFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma1071ScheduleNextRecvPortMatrixSinglepathFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma1071ScheduleNextRecvPortMatrixSinglepathFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma1071ScheduleNextRecvPortMatrixSinglepathFunctionFailure::GetId() const
{
    return "urma_1071";
}
} // namespace diag
