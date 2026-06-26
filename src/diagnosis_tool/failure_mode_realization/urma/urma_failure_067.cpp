#include "urma_failure_067.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure067> g_urma("urma_067");

bool UrmaFailure067::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("schedule_send") != std::string::npos &&
           message.find("Invalid wr->tjetty: NULL") != std::string::npos;
}

std::string UrmaFailure067::GetName() const
{
    return "schedule状态不满足要求导致发送schedule失败";
}

std::string UrmaFailure067::GetRootCauseDesc() const
{
    return "schedule_send执行发送schedule时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure067::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure067::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure067::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：schedule_send，Invalid wr->tjetty: NULL。";
}

std::string UrmaFailure067::GetId() const
{
    return "urma_067";
}
} // namespace diag
