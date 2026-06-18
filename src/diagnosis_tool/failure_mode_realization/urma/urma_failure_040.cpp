#include "urma_failure_040.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure040> g_urma("urma_040");

bool UrmaFailure040::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_close_provider") != std::string::npos &&
           message.find("close failed, err:") != std::string::npos;
}

std::string UrmaFailure040::GetName() const
{
    return "closeclose、provider执行失败导致closeclose、provider失败";
}

std::string UrmaFailure040::GetRootCauseDesc() const
{
    return "urma_close_"
           "provider执行closeclose、provider时依赖的closeclose、provider步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure040::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure040::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure040::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_close_provider，close failed, err:。";
}

std::string UrmaFailure040::GetId() const
{
    return "urma_040";
}
} // namespace diag
