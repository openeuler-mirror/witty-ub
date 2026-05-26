#include "kvcache_conn_fault_006_002.h"
#include "../../failure_mode_factory.h"
#include "kvcache_log_helper.h"

namespace diag {

// 故障编码: kvcache_conn_fault_006_002 (来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L329, L332-333, L193, L217)
static AutoRegister<KvcacheConnFault006_002> g_kvcacheconnfault006_002("kvcache_conn_fault_006_002");

bool KvcacheConnFault006_002::IsValid()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L329, L332-333, L193, L217
    std::string grepOutput = kvcache_log_helper::RunCommand(
        "test -n \"$WITTY_UB_CLIENT_ACCESS_LOG\" && grep -E 'etcd is (timeout|unavailable)' $WITTY_UB_WORKER_INFO_LOG $WITTY_UB_CLIENT_INFO_LOG 2>/dev/null | tail -20");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    // 处理多文件grep输出，去掉"文件路径:"前缀，只保留日志行 (规则h)
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/SKILL.md 规则h
    grepOutput = kvcache_log_helper::StripFilepathPrefixFromOutput(grepOutput);
    kvcache_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string KvcacheConnFault006_002::GetName() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L329, L332-333, L193, L217
    return "code=5 + etcd is timeout/unavailable (三方etcd)";
}

std::string KvcacheConnFault006_002::GetRootCauseDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L329, L332-333, L193, L217
    return "etcd集群或到etcd的网络问题，属于三方etcd责任。（来源：08手册:L217）";
}

RootCause KvcacheConnFault006_002::AnalyzeRootCause()
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L329, L332-333, L193, L217
    return RootCause(true, GetRootCauseDesc());
}

std::string KvcacheConnFault006_002::GetFixSuggDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L329, L332-333, L193, L217
    return "systemctl status etcd；etcdctl endpoint status；排查到etcd的网络。（来源：08手册:L273）";
}

std::string KvcacheConnFault006_002::GetValidationMethodDesc() const
{
    // 来源: .opencode/skills/kvcache-diagnosis-conn-fault-code-generalizer/references/kvcache_conn_fault_mode.md:L329, L332-333, L193, L217
    return "通过日志关键字识别（来源：08手册:L193, L217）：匹配etcd is timeout或etcd is unavailable。（来源：08手册:L193, L217）";
}

std::string KvcacheConnFault006_002::GetId() const
{
    return "kvcache_conn_fault_006_002";
}

} // namespace diag
