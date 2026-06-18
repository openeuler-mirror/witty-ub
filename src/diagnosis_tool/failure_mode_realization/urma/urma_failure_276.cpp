#include "urma_failure_276.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure276> g_urma("urma_276");

bool UrmaFailure276::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_str_to_eid") != std::string::npos && message.find("format error:") != std::string::npos;
}

std::string UrmaFailure276::GetName() const
{
    return "STR、EID状态不满足要求导致strSTR、EID失败";
}

std::string UrmaFailure276::GetRootCauseDesc() const
{
    return "urma_str_to_eid执行strSTR、EID时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure276::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure276::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure276::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_str_to_eid，format error:。";
}

std::string UrmaFailure276::GetId() const
{
    return "urma_276";
}
} // namespace diag
