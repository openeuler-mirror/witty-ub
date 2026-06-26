#include "urma_failure_275.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure275> g_urma("urma_275");

bool UrmaFailure275::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_str_to_eid") != std::string::npos &&
           message.find("Invalid argument.") != std::string::npos;
}

std::string UrmaFailure275::GetName() const
{
    return "STR、EID状态不满足要求导致strSTR、EID失败";
}

std::string UrmaFailure275::GetRootCauseDesc() const
{
    return "urma_str_to_eid执行strSTR、EID时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure275::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure275::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure275::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_str_to_eid，Invalid argument.。";
}

std::string UrmaFailure275::GetId() const
{
    return "urma_275";
}
} // namespace diag
