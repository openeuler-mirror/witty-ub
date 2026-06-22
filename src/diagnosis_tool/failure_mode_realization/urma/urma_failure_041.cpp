#include "urma_failure_041.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure041> g_urma("urma_041");

bool UrmaFailure041::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_open_provider") != std::string::npos &&
           message.find("doesn't exist or doesn't have permission.") != std::string::npos;
}

std::string UrmaFailure041::GetName() const
{
    return "provider状态不满足要求导致打开provider失败";
}

std::string UrmaFailure041::GetRootCauseDesc() const
{
    return "urma_open_provider执行打开provider时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure041::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure041::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure041::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_open_provider，doesn't exist or doesn't have permission.。";
}

std::string UrmaFailure041::GetId() const
{
    return "urma_041";
}
} // namespace diag
