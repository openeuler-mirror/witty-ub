#include "urma_0267_schedule_next_route_matrix_server_singlepath_invalid_single_path_port.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0267ScheduleNextRouteMatrixServerSinglepathInvalidSinglePathPort> g_urma("urma_0267");

bool Urma0267ScheduleNextRouteMatrixServerSinglepathInvalidSinglePathPort::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {
        "Invalid single path port. Single path mode only support RC and need to call bind_jetty"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0267ScheduleNextRouteMatrixServerSinglepathInvalidSinglePathPort::GetName() const
{
    return "schedule_next_route_in_matrix_server_singlepath Invalid single path port. Single pat";
}

std::string Urma0267ScheduleNextRouteMatrixServerSinglepathInvalidSinglePathPort::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "-1";
}

RootCause Urma0267ScheduleNextRouteMatrixServerSinglepathInvalidSinglePathPort::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0267ScheduleNextRouteMatrixServerSinglepathInvalidSinglePathPort::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0267ScheduleNextRouteMatrixServerSinglepathInvalidSinglePathPort::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid single path port. Single path mode only support RC and "
           "need to call bind_jetty";
}

std::string Urma0267ScheduleNextRouteMatrixServerSinglepathInvalidSinglePathPort::GetId() const
{
    return "urma_0267";
}
} // namespace diag
