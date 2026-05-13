#include "urma_0266_schedule_next_route_matrix_server_singlepath_function_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"

namespace diag {

static AutoRegister<Urma0266ScheduleNextRouteMatrixServerSinglepathFunctionFailure> g_urma("urma_0266");

bool Urma0266ScheduleNextRouteMatrixServerSinglepathFunctionFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> subFailureIds = {"urma_0267"};
    for (const auto &subFailureId : subFailureIds) {
        auto failureMode = FailureModeFactory::Instance().Create(subFailureId);
        if (failureMode != nullptr && failureMode->IsValid(logContent)) {
            return true;
        }
    }
    logContent.clear();
    return false;
}

std::string Urma0266ScheduleNextRouteMatrixServerSinglepathFunctionFailure::GetName() const
{
    return "schedule_next_route_in_matrix_server_singlepath 函数故障";
}

std::string Urma0266ScheduleNextRouteMatrixServerSinglepathFunctionFailure::GetRootCauseDesc() const
{
    return "当前函数直接错误日志向下级匹配；调用栈关系仅用于辅助定位上下游，不复制下游内部故障。";
}

RootCause Urma0266ScheduleNextRouteMatrixServerSinglepathFunctionFailure::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string Urma0266ScheduleNextRouteMatrixServerSinglepathFunctionFailure::GetFixSuggDesc() const
{
    return "向下级匹配。";
}

std::string Urma0266ScheduleNextRouteMatrixServerSinglepathFunctionFailure::GetValidationMethodDesc() const
{
    return "向下级匹配。";
}

std::string Urma0266ScheduleNextRouteMatrixServerSinglepathFunctionFailure::GetId() const
{
    return "urma_0266";
}
} // namespace diag
