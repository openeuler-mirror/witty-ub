#include "urma_failure_492.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure492> g_urma("urma_492");

bool UrmaFailure492::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_wait_jfc") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure492::GetName() const
{
    return "dp_ops、wait_jfc、jfc_cnt、JFC无效导致waitWAIT、JFC失败";
}

std::string UrmaFailure492::GetRootCauseDesc() const
{
    return "urma_wait_jfc用于waitWAIT、JFC，调用方传入的dp_ops、wait_jfc、jfc_"
           "cnt、JFC不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure492::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure492::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure492::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_wait_jfc，Invalid parameter.。";
}

std::string UrmaFailure492::GetId() const
{
    return "urma_492";
}
} // namespace diag
